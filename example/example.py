from dataclasses import dataclass
from pathlib import Path

from minimal_configclasses import simple_configclass


@simple_configclass("myexample")
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
