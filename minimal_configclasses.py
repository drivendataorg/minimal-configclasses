import argparse
import dataclasses
from functools import wraps
from itertools import chain
import os
from pathlib import Path
import platform
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
    Union,
    get_type_hints,
)

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib

try:
    from typing import TypeAlias, TypeGuard  # type: ignore[attr-defined] # Python 3.10+
except ImportError:
    from typing_extensions import TypeAlias, TypeGuard

try:
    from typing import get_origin  # Python 3.8+
except ImportError:
    from typing_extensions import get_origin


Loader: TypeAlias = Callable[[type], Mapping[str, Any]]
"""Type alias for loader callables. A valid loader returns a Mapping (e.g., dictionary or
dictionary-like object) containing configuration data. It takes the configclass data class as an
argument so that the it may have its behavior depend on the data class definition."""

LOADERS_ATTR = "__configclass_loaders__"
RESOLVE_SOURCES_METHOD = "__configclass_resolve_sources__"


@classmethod  # type: ignore[misc]
def _resolve_sources_method(cls) -> Mapping[str, Any]:
    """Class method to load and resolve configuration data. Loaders are called in defined order,
    and duplicate keys are resolved with "last-seen wins" logic. This method is added to a
    configclass by the configclass decorator.
    """
    loaders = getattr(cls, LOADERS_ATTR)
    resolved = {}
    for loader in loaders:
        resolved.update(loader(cls))
    return resolved


def custom_configclass(
    loaders: Sequence[Loader],
) -> Callable[[type], type]:
    """Returns a decorator that adds functionality to a data class to load default values from
    specified sources. This is the general decorator factory that provides the ability to fully
    customize behavior. The decorated class must use dataclasses-like initialization semantics,
    meaning that it has an __init__ signature that can accept its attributes as keyword arguments.

    You must specify one or more loaders, which are responsible for loading configuration data from
    some source. When the decorated class is initialized, it will call the loaders in order to load
    configuration data. Keys that are duplicated across sources will be resolved with "last-seen
    wins" priority. The resolved configuration data will be injected into the initialization of the
    decorated data class in between any runtime-specified arguments and the defaults that are
    defined on the data class.

    Arguments:
        loaders (Sequence[Loader]): A sequence of callables that return configuration data loaded
            from some source. See [Loader][minimal_configclasses.Loader] for the correct signature
            and documentation.
    """

    def configclass_decorator(cls: type) -> type:
        setattr(cls, LOADERS_ATTR, loaders)
        setattr(cls, RESOLVE_SOURCES_METHOD, _resolve_sources_method)
        original_init = cls.__init__  # type: ignore[misc]

        @wraps(original_init)
        def init_wrapper(self, *args, **kwargs):
            # Merge resolved data with kwargs. kwargs has priority
            # resolved, metadata = resolve_sources(self)
            # kwargs = {**resolved, **kwargs}
            # self.__metadata__ = metadata
            kwargs = {**resolve_sources(self), **kwargs}
            original_init(self, *args, **kwargs)

        cls.__init__ = init_wrapper  # type: ignore[misc]
        return cls

    return configclass_decorator


def loaders(
    obj: Any,
) -> Sequence[Callable[[type], Iterator[Tuple[Mapping[str, Any], Mapping]]]]:
    """Returns the sequence of loader callables added to a configclass."""
    try:
        return getattr(obj, LOADERS_ATTR)
    except AttributeError:
        raise TypeError("Must be called with configclass type or instance.")


def resolve_sources(obj: Any) -> Mapping[str, Any]:
    """Given a configclass or configclass instance, call each attached loader in sequence and
    resolve the loaded data with "last-seen wins" priority. This function works by calling an
    internal class method that is added by the configclass decorator.
    """
    try:
        return getattr(obj, RESOLVE_SOURCES_METHOD)()
    except AttributeError:
        raise TypeError("Must be called with configclass type or instance.")


def is_configclass(obj: Any) -> bool:
    """Returns `True` if its parameter is a configclass or an instance of a configclass, otherwise
    returns `False`. This is determined by a simple check for the internal class method to resolve
    sources that is created by the configclass decorator.

    If you need to know if the input is an instance of a configclass (and not a configclass
    itself), then add a further check for not `isinstance(obj, type)`.
    """
    cls = obj if isinstance(obj, type) else type(obj)
    return hasattr(cls, RESOLVE_SOURCES_METHOD)


def is_dict_with_str_keys(d: Any) -> TypeGuard[Dict[str, Any]]:
    return isinstance(d, dict) and all(isinstance(k, str) for k in d)


def load_toml(path: Path, namespace: Sequence[str] = ()) -> Dict[str, Any]:
    """Loads data from the specified namespace of a TOML file at the specified path."""
    with path.open("rb") as fp:
        data = tomllib.load(fp)
    if namespace:
        for ind, part in enumerate(namespace):
            try:
                data = data[part]
            except TypeError:
                namespace_path = ".".join(namespace[: ind + 1])
                raise TypeError(f"Expected {namespace_path} to be a TOML table. Got: {type(data)}")
    if not is_dict_with_str_keys(data):
        namespace_path = ".".join(namespace[: ind + 1])
        raise TypeError(f"Expected {namespace_path} to be a TOML table. Got: {type(data)}")
    return data


RuntimeSpecifiedPathHook: TypeAlias = Callable[[], Union[str, Path]]
"""Type alias for a valid runtime-specified path hook that can be optionally specified when
constructing a TomlFileLoader."""


@dataclasses.dataclass
class TomlFileLoader:
    """Constructs a loader callable that searches for a valid TOML configuration file with an entry
    that matches the provided namespace idenfication sequence. It will return the data from the
    first one found and stop searching, even if it is empty. The only required argument is the
    namespace sequence.

    pyproject.toml files will check for data under the provided namespace nested under [tool], per
    PEP 518's specification for tool-specific configuration data. Named configuration files will
    use the first part of the provided namespace to construct the filenames to search for, and use
    any remaining namespace parts inside the TOML data structure.

    This loader uses the following search strategy:

      - Search current working directory for pyproject.toml, then named files.
      - Search ancestor direcotires for pyproject.toml, then named files, until encountering a
        repository root or the filesystem root.
      - Search the XDG Config Home user directory for named files.
      - Search the macOS ~/Library/Application Support/ user app data directory for named files, if
        on macOS.
      - Search the Windows %AppData% user roaming app data directory for named files, if on
        Windows.
      - Search the user home directory for named files.

    The search strategy can be customized by the optional parameters.

    Arguments:
        namespace (Sequence[str]): Namespace to search file for configuration data, with parts
            separated into a sequence. For pyproject.toml files, this will search the
            [tool.{ns0}.{ns1}.{...}] table. For named files, it will use the first item as the
            filename and remaining items for tables inside the file [{ns1}.{...}].
        convert_hyphens (bool): Whether to convert hyphens in key names to underscores upon loading
            the data. Defaults to True.
        runtime_specified_path_hook (RuntimeSpecifiedPathHook): Optional callable hook that allows
            a runtime-specified path to be set as the first item of the search strategy. This can
            be used for the case that your application allows users to specify a path to a
            configuration file.
        check_pyproject_toml (bool): Whether to include pyproject.toml files when searching for a
            configuration file.
        named_file_templates (Sequence[str]): Templates for named configuration files. Each template
            should contain exactly one replacement field, which will be substituted with the first
            item of the namespace sequence. Defaults to ('{}.toml', ".{}.toml").
        search_ancestor_dirs (bool): Whether to include ancestor directories when searching for a
            valid configuration file. Defaults to True.
        stop_on_repo_root (bool): Whether to stop searching ancestor directories when encountering
            a directory containing .git, .hg, or .svn. This option only has an effect when
            search_ancestor_dirs is True. Defaults to True.
        check_xdg_config_home_dir (bool): Whether to include $XDG_CONFIG_HOME when searching for
            valid configuration files. If the environment variable $XDG_CONFIG_HOME is not set, this
            will check $HOME/.config/.
        check_macos_application_support_dir (bool): Whether to include the standard macOS location
            for application data, $HOME/Library/Application Support/, when searching for valid
            configuration files. This option only has an effect when on macOS. Defaults to True.
        check_windows_appdata_dir (bool): Whether to include the standard Windows location for
            user application data, %AppData%, when searching for valid configuration files. If the
            environment variable $APPDATA is not set, this will check $HOME\\AppData\\Roaming\\.
            This option only has an effect when on Windows. Defaults to True.
        check_home_dir (bool): Whether to include the user's home directory when searching for
            valid configuration files. Defaults to True.
    """

    namespace: Sequence[str]
    convert_hyphens: bool = True
    runtime_specified_path_hook: Optional[RuntimeSpecifiedPathHook] = None
    check_pyproject_toml: bool = True
    named_file_templates: Sequence[str] = ("{}.toml", ".{}.toml")
    search_ancestor_dirs = True
    stop_on_repo_root = True
    check_xdg_config_home_dir: bool = True
    check_macos_application_support_dir: bool = True
    check_windows_appdata_dir: bool = True
    check_home_dir: bool = True

    def __post_init__(self):
        if len(self.namespace) < 1:
            raise ValueError("namespace sequence must contain at least one part.")

    @property
    def file_names(self) -> Iterator[str]:
        for template in self.named_file_templates:
            yield template.format(self.namespace[0])

    @property
    def paths_to_check(self) -> Iterator[Path]:
        if self.runtime_specified_path_hook:
            yield Path(self.runtime_specified_path_hook())

        cwd = Path.cwd()
        dirs_to_search: Iterable[Path] = [cwd]
        if self.search_ancestor_dirs:
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

        if self.check_xdg_config_home_dir:
            xdg_config_home_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
            for file_name in self.file_names:
                yield xdg_config_home_dir / file_name
        if self.check_macos_application_support_dir and platform.system() == "Darwin":
            for file_name in self.file_names:
                yield Path.home() / "Library" / "Application Support" / file_name
        if self.check_windows_appdata_dir and platform.system() == "Windows":
            windows_appdata_dir = Path(
                os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
            )
            for file_name in self.file_names:
                yield windows_appdata_dir / file_name
        if self.check_home_dir:
            for file_name in self.file_names:
                yield Path.home() / file_name

    def __call__(self, data_class: type) -> Dict[str, Mapping]:
        for path in self.paths_to_check:
            try:
                if path.name == "pyproject.toml":
                    namespace = ("tool",) + tuple(self.namespace)
                else:
                    namespace = namespace[1:]
                data = load_toml(path, namespace)
                if self.convert_hyphens:
                    data = {key.replace("-", "_"): value for key, value in data.items()}
                return data
            except KeyError:
                # This is fine because configuration is optional, check next one
                pass
            except FileNotFoundError:
                # This is fine because configuration is optional, check next one
                pass
        return {}


def convert_to_type(val: str, type_: type) -> Any:
    """Converts a string value to the specified type for the following primitive types and
    built-in containers: int, float, complex, bytes, bool, list, tuple, dict. If the type is not
    supported, the original value will be returned.
    """
    if type_ in {int, float, complex}:
        return type_(val)
    elif type_ is bytes:
        return val.encode("utf-8")
    elif type_ is bool:
        if val.lower() == "true":
            return True
        elif val.lower() == "false":
            return False
        else:
            raise ValueError("Unable to convert bool value:", val)
    elif type_ in {list, tuple, dict}:
        return type_(tomllib.loads(f"val = {val}")["val"])
    elif get_origin(type_) in {list, tuple, dict}:
        return get_origin(type_)(tomllib.loads(f"val = {val}")["val"])  # type: ignore[misc]
    return val


@dataclasses.dataclass
class EnvVarLoader:
    """Constructs a loader callable that returns configuration data from environment variables
    matching the given namespace identification sequence. Namespace parts are uppercased, joined by
    underscore, and then used as a prefix.

    Arguments:
        namespace (Sequence[str]): Namespace to search for environment variables.
        convert_types (bool): Whether to convert loaded environment variable data to the annotated
            types on the configclass. Requires that the data class uses dataclasses-style member
            declaration with type annotations.
        to_field_name_transform (Callable[[str], str]): A callable that transforms the environment
            variable name (after the namespace prefix has been removed) to its associated
            configclass variable name. Defaults to lowercasing.
    """

    namespace: Sequence[str]
    convert_types: bool = True
    to_field_name_transform: Callable[[str], str] = lambda s: s.lower()  # noqa: E731

    @property
    def prefix(self) -> str:
        return "_".join(n.upper() for n in self.namespace) + "_"

    @property
    def env_vars(self) -> Iterator[Tuple[str, str]]:
        for key, val in os.environ.items():
            if key.startswith(self.prefix):
                yield key, val

    def __call__(self, data_class: type) -> Dict[str, Any]:
        if self.convert_types:
            field_type_hints = get_type_hints(data_class)
        else:
            field_type_hints = {}
        data = {}
        for key, val in self.env_vars:
            field_name = self.to_field_name_transform(key[len(self.prefix) :])
            if field_name in field_type_hints:
                val = convert_to_type(val, field_type_hints[field_name])
            data[field_name] = val
        return data


@dataclasses.dataclass
class ArgParseLoader:
    """Constructs a loader callable from a argparse.ArgumentParser instance."""

    parser: argparse.ArgumentParser

    def __call__(self, data_class: type) -> Dict[str, Any]:
        return vars(self.parser.parse_args())


def configclass(
    *namespace: str,
    runtime_specified_path_hook: Optional[RuntimeSpecifiedPathHook] = None,
    argument_parser: Optional[argparse.ArgumentParser] = None,
) -> Callable[[type], type]:
    """Returns a decorator that adds functionality to a data class to load default values from
    certain sources. This is the out-of-the-box decorator factory that implements sane, default
    behavior that should apply directly to most use cases. By default, the decorated data class
    will load configuration data from an automatically-discovered TOML configuration file and from
    environment variables during initialization. Initializing the decorated class will resolve data
    with the following order of increasing priority: class defaults < TOML file < environment
    variables < runtime-specified arguments. The only required argument is at least one namespace
    string that will be used to identify relevant TOML file data and environment variables.

    Optional arguments include a runtime hook that returns a file path to a TOML file, and an
    argparse parser instance that will be used as another data source. If further customization is
    needed, see [custom_configclass][minimal_configclasses.custom_configclass].

    The decorated class must use dataclasses-like initialization semantics, meaning that it has an
    __init__ signature that can accept its attributes as keyword arguments.

    Arguments:
        *namespace (str): Namespace identifier. If more than one, this is treated as the identifier
            path for a nested namespace.
        runtime_specified_path_hook (Optional[RuntimeSpecifiedPathHook]): Optional callable hook
            that allows a runtime-specified path to be passed checked by the TomlFileLoader. This
            can be used for the case that your program allows users to specify a path to a
            configuration file. Defaults to None.
        argument_parser (Optional[argparse.ArgumentParser]): Optional ArgumentParser instance. If
            provided, will append an ArgParseLoader to the loaders as the data source with highest
            priority. Defaults to None.
    """
    if len(namespace) < 1 or isinstance(namespace[0], type):
        raise ValueError(
            "configclass must be called with at least one namespace argument, e.g., "
            "@configclass('myproject')"
        )
    loaders = [
        TomlFileLoader(namespace, runtime_specified_path_hook=runtime_specified_path_hook),
        EnvVarLoader(namespace),
    ]
    if argument_parser:
        loaders.append(ArgParseLoader(argument_parser))
    return custom_configclass(loaders=loaders)
