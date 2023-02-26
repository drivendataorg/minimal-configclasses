from collections import ChainMap
from dataclasses import dataclass
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
)

try:
    from typing import TypeGuard  # type: ignore[attr-defined]
except ImportError:
    from typing_extensions import TypeGuard

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


def is_dict_with_str_keys(d: Any) -> TypeGuard[Dict[str, Any]]:
    return isinstance(d, dict) and all(isinstance(k, str) for k in d)


@dataclass
class TomlFileLoader:
    name: str
    convert_hyphens: True
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

    def __call__(self) -> Iterator[Tuple[Dict[str, Any], dict]]:
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


@dataclass
class ConfigEnvVarLoader:
    name: str

    @property
    def prefix(self):
        return self.name.upper() + "_"

    def env_var_to_field_name(self, env_var: str):
        return env_var[len(self.prefix) :].lower()

    def __call__(self) -> Iterator[Tuple[Dict[str, Any], dict]]:
        yield {
            self.env_var_to_field_name(key): value
            for key, value in os.environ.items()
            if key.startswith(self.prefix)
        }, {"loader": self}


class FirstOnlyResolver:
    def __call__(self, sources: Iterator[Tuple[Dict[str, Any], dict]]) -> dict:
        return next(sources)[0]


@dataclass
class MergeResolver:
    n: Optional[int] = None

    def __call__(self, sources: Iterator[Tuple[Dict[str, Any], dict]]) -> Mapping[str, Any]:
        if self.n is None:
            return ChainMap(*(item[0] for item in sources))
        else:
            return ChainMap(*(item[0] for item in islice(sources, self.n)))


def simple_configclass(name: str) -> Callable[[type], type]:
    return configclass(
        loaders=[
            ConfigEnvVarLoader("name"),
            TomlFileLoader("name"),
        ],
        resolver=MergeResolver(),
    )


def configclass(
    loaders: Sequence[Callable[[], Iterator[Tuple[Dict[str, Any], dict]]]],
    resolver: Callable[[Iterator[Tuple[Dict[str, Any], dict]]], Mapping[str, Any]],
) -> Callable[[type], type]:
    @classmethod  # type: ignore[misc]
    def resolve_sources(cls) -> Mapping:
        file_data = chain(*(loader() for loader in loaders))
        return resolver(file_data)

    def decorator(cls):
        cls.resolve_sources = resolve_sources
        original_init = cls.__init__

        def init_wrapper(self, *args, **kwargs):
            kwargs = {**self.resolve_sources(), **kwargs}
            original_init(self, *args, **kwargs)

        cls.__init__ = init_wrapper
        return cls

    return decorator
