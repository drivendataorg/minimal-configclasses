# minimal-configclasses

**A minimal Python library for creating config classes: a data class that can load defaults from other sources.**

- Dead easy API: stack a `@configclass` decorator on any class with dataclass-like initialization semantics, such as standard library dataclasses, a Pydantic `BaseModel`, or even NamedTuples and SimpleNamespaces.
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

## simple_configclass

...

## Supplying your own loaders and resolvers

...

### Custom loaders

...

### Custom resolvers

...

## Limitations and Design Trade-offs

- **Only TOML config files have out-of-the-box support.** In order to keep this library simple and minimal, we only support loading config files in TOML format. Python has adopted `pyproject.toml` as a standard place for tools to read configuration data ([PEP 518](https://peps.python.org/pep-0518/#tool-table)). Reading TOML is available as part of the tomllib standard library module since Python 3.11, and it is available to earlier Python versions from the zero-dependency backport library [tomli](https://github.com/hukkin/tomli). You can easily implement your own loader for other file formats, such as INI files and YAML. See ["Custom loaders"](#custom-loaders).
- **No out-of-the-box support in general for type conversion or data validation.** The only exception is basic type casting for environment variables when used with dataclasses. Type conversions and data validation is a complex area and out of scope for this library. If you need conversion or validation, you have several options:
    - Implement your own logic in custom loaders. See ["Custom loaders"](#custom-loaders).
    - Implement as part of your data class. For example, dataclasses support a [`__post_init__` method](https://docs.python.org/3/library/dataclasses.html#post-init-processing) for post-initialization processing.
    - Use minimal-configclasses in combination with other libraries that provide this functionality, such as [Pydantic](https://docs.pydantic.dev/).
