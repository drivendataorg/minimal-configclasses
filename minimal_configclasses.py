import dataclasses
from itertools import chain, islice
import os
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    get_type_hints,
)

try:
    from typing import TypeGuard  # type: ignore[attr-defined]
except ImportError:
    from typing_extensions import TypeGuard

try:
    from typing import get_origin
except ImportError:
    from typing_extensions import get_origin


try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


def is_dict_with_str_keys(d: Any) -> TypeGuard[Dict[str, Any]]:
    return isinstance(d, dict) and all(isinstance(k, str) for k in d)


@dataclasses.dataclass
class TomlFileLoader:
    name: str
    convert_hyphens: bool = True
    check_pyproject_toml: bool = True
    file_name_templates: Iterable[str] = ("{name}.toml", ".{name}.toml")
    recursive_search = True
    stop_on_repo_root = True
    check_home_dir: bool = True
    check_xdg_config_home_dir: bool = True

    @property
    def file_names(self) -> Iterator[str]:
        for template in self.file_name_templates:
            yield template.format(name=self.name)

    @property
    def paths_to_check(self) -> Iterator[Path]:
        cwd = Path.cwd()
        dirs_to_search: Iterable[Path] = [cwd]
        if self.recursive_search:
            dirs_to_search = chain(dirs_to_search, cwd.parents)
        for dir in dirs_to_search:
            if self.check_pyproject_toml:
                yield dir / "pyproject.toml"
            for file_name in self.file_names:
                yield dir / file_name
            if self.stop_on_repo_root and any(
                (dir / repo).exists() for repo in (".git", ".hg", ".svn")
            ):
                break

        if self.check_home_dir:
            for file_name in self.file_names:
                yield dir / file_name
        if self.check_xdg_config_home_dir:
            for file_name in self.file_names:
                yield dir / file_name

    def load(self, path: Path) -> Dict[str, Any]:
        with path.open("rb") as fp:
            data = tomllib.load(fp)
        if path.name == "pyproject.toml":
            if is_dict_with_str_keys(data["tool"][self.name]):
                return data["tool"][self.name]
            else:
                raise TypeError(
                    f"tool.{self.name} must be a TOML table. "
                    f"Got: {type(data['tool'][self.name])}"
                )
        else:
            return data

    def __call__(self, data_class: type) -> Iterator[Tuple[Mapping[str, Mapping], Mapping]]:
        for path in self.paths_to_check:
            try:
                data = self.load(path)
                if self.convert_hyphens:
                    data = {key.replace("-", "_"): value for key, value in data.items()}
                yield (data, {"loader": self, "path": path})
            except FileNotFoundError:
                pass
            except KeyError as e:
                if e.args not in {("tool",), (self.name,)}:
                    raise


@dataclasses.dataclass
class EnvVarLoader:
    name: str
    convert_types: bool = True

    @property
    def prefix(self):
        return self.name.upper() + "_"

    def env_var_to_field_name(self, env_var: str):
        return env_var[len(self.prefix) :].lower()

    def convert_env_var_to_type(self, val: str, field_type):
        if field_type in {int, float, complex}:
            return field_type(val)
        elif field_type is bytes:
            return val.encode("utf-8")
        elif field_type is bool:
            if val.lower() == "true":
                return True
            elif val.lower() == "false":
                return False
            else:
                raise ValueError("Unable to convert bool value:", val)
        elif get_origin(field_type) in {list, tuple, dict}:
            return get_origin(field_type)(  # type: ignore[misc]
                tomllib.loads(f"val = {val}")["val"]
            )
        return val

    def __call__(self, data_class: type) -> Iterator[Tuple[Mapping[str, Any], Mapping]]:
        data = {
            self.env_var_to_field_name(key): value
            for key, value in os.environ.items()
            if key.startswith(self.prefix)
        }
        if self.convert_types:
            if dataclasses.is_dataclass(data_class):
                field_type_hints = get_type_hints(data_class)
                data = {
                    key: self.convert_env_var_to_type(value, field_type_hints[key])
                    for key, value in data.items()
                }
            else:
                # Not a dataclass
                pass
        yield data, {"loader": self}


class FirstOnlyResolver:
    def __call__(
        self, sources: Iterator[Tuple[Mapping[str, Any], Mapping]], data_class: type
    ) -> Mapping:
        return next(sources)[0]


_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


@dataclasses.dataclass
class MergeResolver:
    n: Optional[int] = None

    def __call__(
        self, sources: Iterator[Tuple[Mapping[str, Any], Mapping]], data_class: type
    ) -> Mapping[str, Any]:
        if self.n is not None:
            sources = islice(sources, self.n)
        # collections.ChainMap has annoying typing properties because it is mutable
        # https://github.com/python/typeshed/issues/8430
        # Use dict with itertools.chain instead
        return dict(chain.from_iterable(s[0].items() for s in reversed(tuple(sources))))


LOADERS_ATTR = "__configclass_loaders__"
RESOLVER_ATTR = "__configclass_resolver__"
RESOLVE_SOURCES_METHOD = "__configclass_resolve_sources__"


def loaders(obj) -> Sequence[Callable[[type], Iterator[Tuple[Mapping[str, Any], Mapping]]]]:
    """Returns the sequence of loader callables added to a configclass."""
    try:
        return getattr(obj, LOADERS_ATTR)
    except AttributeError:
        raise TypeError("Must be called with configclass type or instance.")


def resolver(
    obj,
) -> Callable[[Iterator[Tuple[Mapping[str, Any], Mapping]], type], Mapping[str, Any]]:
    """Returns the resolver callable added to a configclass."""
    try:
        return getattr(obj, RESOLVER_ATTR)
    except AttributeError:
        raise TypeError("Must be called with configclass type or instance.")


@classmethod  # type: ignore[misc]
def _resolve_sources_method(cls) -> Mapping[str, Any]:
    """Class method to load and resolve configuration data. Added to a configclass by the
    configclass decorator.
    """
    loaders = getattr(cls, LOADERS_ATTR)
    resolver = getattr(cls, RESOLVER_ATTR)
    config_data = chain(*(loader(cls) for loader in loaders))
    return resolver(config_data, cls)


def resolve_sources(obj) -> Mapping[str, Any]:
    """Given a configclass or configclass instance, loads configuration data and resolves them
    according to the configclass' loaders and resolver.
    """
    try:
        return getattr(obj, RESOLVE_SOURCES_METHOD)()
    except AttributeError:
        raise TypeError("Must be called with configclass type or instance.")


def configclass(
    loaders: Sequence[Callable[[type], Iterator[Tuple[Mapping[str, Any], Mapping]]]],
    resolver: Callable[[Iterator[Tuple[Mapping[str, Any], Mapping]], type], Mapping[str, Any]],
) -> Callable[[type], type]:
    def configclass_decorator(cls: type) -> type:
        setattr(cls, LOADERS_ATTR, loaders)
        setattr(cls, RESOLVER_ATTR, resolver)
        setattr(cls, RESOLVE_SOURCES_METHOD, _resolve_sources_method)
        original_init = cls.__init__  # type: ignore[misc]

        def init_wrapper(self, *args, **kwargs):
            # Merge resolved data with kwargs. kwargs has priority
            kwargs = {**resolve_sources(self), **kwargs}
            original_init(self, *args, **kwargs)

        cls.__init__ = init_wrapper  # type: ignore[misc]
        return cls

    return configclass_decorator


def is_configclass(obj: Any) -> bool:
    """Returns `True` if its parameter is a configclass or an instance of a configclass, otherwise
    returns `False`. This is determined by a simple

    If you need to know if the input is an instance of a configclass (and not a configclass
    itself), then add a further check for not `isinstance(obj, type)`.
    """
    cls = obj if isinstance(obj, type) else type(obj)
    return hasattr(cls, RESOLVE_SOURCES_METHOD)


def simple_configclass(name: str) -> Callable[[type], type]:
    if isinstance(name, type):
        raise ValueError(
            "simple_configclass must be called with a name argument, e.g., "
            "@simpleconfig_class(name=...)"
        )
    return configclass(
        loaders=[
            EnvVarLoader(name),
            TomlFileLoader(name),
        ],
        resolver=MergeResolver(),
    )
