# minimal-configclasses

**A minimal Python library for creating config classes: a data class that can load defaults from other sources.**

- Dead easy API: stack a `@configclass` decorator on any class with dataclass-like initialization semantics, such as standard library [dataclasses](https://docs.python.org/3/library/dataclasses.html), a [Pydantic `BaseModel`](https://docs.pydantic.dev/usage/models/), or [attrs classes](https://www.attrs.org/en/stable/overview.html).
- A sane out-of-the-box implemention `@simple_configclass` that merges values from environment variables, `pyproject.toml` files, and TOML config files in conventional locations.
- Simple and straightforward extensibility: write loader functions that load source data into dictionaries and resolver functions that resolve multiple dictionaries into one.
- Zero dependencies for 3.11 or higher, and only standard library backports for lower Python versions.

```python
from dataclasses import dataclass
from pathlib import Path

from minimal_configclasses import simple_configclass


@simple_configclass(name="myexample")
@dataclass
class MyExampleConfig:
    var_a: int = 0
    var_b: bool = False
    var_c: str = "default"


print(Path("pyproject.toml").read_text())
# > [tool.myexample]
# > var_a = 100
# > var_c = "custom"

# Resolution order: specified values > loaded sources > defaults
config = MyExampleConfig(var_a=9001)
config
# > MyExampleConfig(var_a=9001, var_b=False, var_c='custom')
```

## @simple_configclass: Out-of-the-box functionality

The `@simple_configclass` decorator provides easy-to-use out-of-the-box functionality. The only required argument is a `name` string that will be used when searching for configuration data:

- Checking for environment variables prefixed by `{name.upper()}_`
- Checking for the `[tool.{name}]` table in any found `project.toml` files
- Checking for files named `{name}.toml` or `.{name}.toml`

If you need additional configurability, check out the general API with the `@configclass` decorator in the next section.

## @configclass: More customizability

The `@configclass` decorator is the general API for setting up a config class. It takes a sequence (e.g., list or tuple) of "loaders" that find and read configuration data, as well as a "resolver" which combines all of the loaded configuration data into one set of values.

minimal-configclasses provides a few built-in loaders and resolvers that you can use. In fact, `@simple_configclass` is just a wrapper around `@configclass` using built-in loaders and a resolver. It is equivalent to:

```python
@configclass(
    loaders=[EnvVarLoader(name), TomlFileLoader(name)],
    resolver=MergeResolver(),
)
```

The built-in loaders have additional parameters you can set when initializing them to modify their behavior—take a look at their documentation to see all of the options.

## Supplying your own loaders and resolvers

If the built-in loaders or resolvers don't meet your needs, you can easily write your own. Loaders and resolvers simply need to be callables that match required argument and return signatures. While the built-in implementations from minimal-configclasses are implemented as classes, valid loaders and resolvers don't need to be classes in general—you can simply write functions. Classes are only necessarily if you want parameterize their behavior for reuse them in different situations.

### Custom loaders

A loader is a callable that returns an iterator of tuples of configuration data and metadata. The simplest version of this would be a generator function. A template for such a generator function is shown below:

```python
def my_loader(data_class: type) -> Iterator[Tuple[Mapping[str, Any], Mapping]]:
    data = ...
    metadata = ...
    yield data, metadata
```

The configuration data and metadata should both be mappings (i.e., dictionary or dictionary-like objects). The first item in the tuple—"data"—is the configuration values read from a source. The second item—"metadata"—is a container for arbitrary metadata that you would like to pass along. This lets you define behavior later in the resolver based on information coming from the loader.

Loaders will called with the config data class as an argument, so that you may use metadata on the data class inside your loader. For example, the built-in `EnvVarLoader` gets the field types from data class' type annotations and attempts to convert the values loaded from environment variables to those types.

The `@configclass` decorator is able to take multiple loaders. It will call each loader in sequence and the full stream of loaded `(data, metadata)` tuples will be passed to the resolver.

### Custom resolvers

A resolver is a callable that takes all `(data, metadata)` tuples from the loaders and resolves everything into a single configuration data mapping (i.e., dictionary or dictionary-like object) that will be passed to data class initialization. A minimal function template is shown below:

```python
def my_resolver(
        sources: Iterator[Tuple[Mapping[str, Any], Mapping]], data_class: type
    ) -> Mapping[str, Any]:
    ...
```

Like the loaders, the resolver is passed the config data class as an argument. This allows you to define behavior that depends information from the data class definition.

## Limitations and Design Trade-offs

- **Only TOML config files have out-of-the-box support.** In order to keep this library simple and minimal, we only support loading config files in TOML format. Python has adopted `pyproject.toml` as a standard place for tools to read configuration data ([PEP 518](https://peps.python.org/pep-0518/#tool-table)). Reading TOML is available as part of the tomllib standard library module since Python 3.11, and it is available to earlier Python versions from the zero-dependency backport library [tomli](https://github.com/hukkin/tomli). You can easily implement your own loader for other file formats, such as INI files and YAML. See ["Custom loaders"](#custom-loaders).
- **No out-of-the-box support in general for type conversion or data validation.** The only exception is basic type casting for environment variables when used with dataclasses. Type conversions and data validation is a complex area and out of scope for this library. If you need conversion or validation, you have several options:
    - Implement your own logic in custom loaders. See ["Custom loaders"](#custom-loaders).
    - Implement as part of your data class. For example, dataclasses support a [`__post_init__` method](https://docs.python.org/3/library/dataclasses.html#post-init-processing) for post-initialization processing.
    - Use minimal-configclasses in combination with other libraries that provide this functionality, such as [Pydantic](https://docs.pydantic.dev/).
