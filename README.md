# minimal-configclasses

**A minimal Python library for creating config classes: a data class that can load defaults from other sources.**

- Dead easy API: stack a `@configclass` decorator on any class with dataclass-like initialization semantics, such as standard library [dataclasses](https://docs.python.org/3/library/dataclasses.html), [Pydantic `BaseModel` classes](https://docs.pydantic.dev/usage/models/), or [attrs classes](https://www.attrs.org/en/stable/overview.html). Inspired by the simple API of dataclasses.
- A sane out-of-the-box default that merges values from environment variables, `pyproject.toml` files, and TOML config files in conventional locations.
- Simple and straightforward extensibility: write loader functions that load source data into dictionaries.
- Zero dependencies for 3.11 or higher, and only standard library backports for lower Python versions.

When you initialize a class decorated by `@configclass`, it will run a hook to load configuration values from certain sources and resolve them into a single set. Those values then get injected in between user-specified arguments and the defaults defined on the class.

```python
from dataclasses import dataclass
from pathlib import Path

from minimal_configclasses import configclass


@configclass("myexample")
@dataclass
class MyExampleConfig:
    var_a: int = 0
    var_b: bool = False
    var_c: str = "default"


print(Path("pyproject.toml").read_text())
#> [tool.myexample]
#> var_a = 100
#> var_c = "from_file"

# Resolution order: specified values > loaded sources > defaults
config = MyExampleConfig(var_a=9001)
config
#> MyExampleConfig(var_a=9001, var_b=False, var_c='from_file')
```

## @configclass: Out-of-the-box functionality

The `@configclass` decorator provides easy-to-use out-of-the-box functionality. All you need to provide is one or more name strings that will be used as a namespace path to search for data. In the simplest case of one name:

- Checking for environment variables prefixed by `{name.upper()}_`
- Checking for the `[tool.{name}]` table in any found `project.toml` files
- Checking for files named `{name}.toml` or `.{name}.toml`

Additional name values will be used as additional namespace layers, e.g., joined to the environment prefix by underscores, or used to index into TOML tables.

If you need additional configurability, check out the general API with the `@custom_configclass` decorator in the next section.

## @custom_configclass: More customizability

The `@custom_configclass` decorator is the general API for setting up a config class. It takes simply a sequence (e.g., list or tuple) of "loaders" that find and read configuration data.

minimal-configclasses provides a few built-in loaders and resolvers that you can use. In fact, `@configclass` is just a wrapper around `@custom_configclass` with using built-in loaders. It is equivalent to:

```python
@custom_configclass(loaders=[EnvVarLoader(names), TomlFileLoader(names)])
```

The built-in loaders have additional parameters you can set when initializing them to modify their behavior—take a look at their documentation to see all of the options.

## Custom loaders

If the built-in loaders don't meet your needs, you can easily write your own. Loaders simply need to be callables (e.g., a function) that match the required argument and return signatures. Here's a basic template for a loader:

```python
def my_loader(data_class: type) -> Mapping[str, Any]:
    data = {}
    return data
```

Loaders will get called with the decorated data class as an argument, and they must return a mapping (i.e., a dictionary or dictionary-like object) containing the configuration data.

The decorated data class is provided in case you need your loader's behavior to depend on it. For example, the built-in `EnvVarLoader` gets the field types from data class' type annotations and attempts to convert the values loaded from environment variables to those types.

Loaders will get called in sequence, and their returned data will be resolved using a "last-seen wins" priority. If you want to use more complicated resolution logic, you can do so by wrapping your loaders inside a custom loader that implements the resolution logic internally.

You may notice that loaders in minimal-configclasses are defined as classes with a `__call__` method. This is only necessary if you plan to parameterize a loader's behavior with options so that they can be reused in different situations. In general, a loader can be as simple as just a function.

minimal-configclasses defines a `Loader` type alias for valid loader callables that you can use for any type-checking needs.

## Limitations and Design Choices

- **Only TOML config files have out-of-the-box support.** In order to keep this library simple and minimal, we only support loading config files in TOML format. Python has adopted `pyproject.toml` as a standard place for tools to read configuration data from ([PEP 518](https://peps.python.org/pep-0518/#tool-table)). Reading TOML is available as part of the tomllib standard library module since Python 3.11, and it is available to earlier Python versions from the zero-dependency backport library [tomli](https://github.com/hukkin/tomli). If you want to read other formats, you can easily implement your own loader for other file formats, such as INI files and YAML. See ["Custom loaders"](#custom-loaders).
    - **Why not JSON?** JSON is not a common format for configuration files.
    - **Why not INI?** TOML files are a modern standard format for Python configuration. If you're newly implementing configuration files for a tool, you should just use TOML.
    - **Why not YAML?** The Python standard library does not include a YAML parser.
- **No out-of-the-box support in general for type conversion or data validation.** The only exception is basic type casting for environment variables when used with a data class that declares attribute types using type hints. Type conversions and data validation is a complex area and out of scope for this library. If you need conversion or validation, you have several options:
    - Implement your own logic in custom loaders. See ["Custom loaders"](#custom-loaders).
    - Implement as part of your data class. For example, dataclasses support a [`__post_init__` method](https://docs.python.org/3/library/dataclasses.html#post-init-processing) for post-initialization processing.
    - Use minimal-configclasses in combination with other libraries that offer conversion and validation features, such as [Pydantic](https://docs.pydantic.dev/) or [attrs](https://www.attrs.org/en/stable/).
