from collections import namedtuple
import dataclasses
import os
from pathlib import Path
from types import SimpleNamespace

import attrs
import pydantic
import pytest
import tomli_w

from minimal_configclasses import simple_configclass


TOOL_NAME = "testtool"


@pytest.fixture
def config_file_data():
    return {"var_int": 100, "var_str": "custom"}


@pytest.fixture
def pyproject_toml_file(config_file_data, tmp_path):
    payload = {"tool": {TOOL_NAME: config_file_data}}
    with (tmp_path / "pyproject.toml").open("wb") as fp:
        tomli_w.dump(payload, fp)

    orig_cwd = Path.cwd()
    os.chdir(tmp_path)
    yield
    os.chdir(orig_cwd)


def test_simple_configclass_dataclass(pyproject_toml_file):
    @simple_configclass(name=TOOL_NAME)
    @dataclasses.dataclass
    class DataClassConfig:
        var_int: int = 0
        var_bool: bool = False
        var_str: str = "default"

    config = DataClassConfig(var_int=9001)
    assert config.var_int == 9001
    assert config.var_bool is False
    assert config.var_str == "custom"


def test_simple_configclass_pydantic(pyproject_toml_file):
    @simple_configclass(name=TOOL_NAME)
    class PydanticConfig(pydantic.BaseModel):
        var_int: int = 0
        var_bool: bool = False
        var_str: str = "default"

    config = PydanticConfig(var_int=9001)
    assert config.var_int == 9001
    assert config.var_bool is False
    assert config.var_str == "custom"


def test_simple_configclass_attrs(pyproject_toml_file):
    @simple_configclass(name=TOOL_NAME)
    @attrs.define
    class AttrsConfig:
        var_int: int = 0
        var_bool: bool = False
        var_str: str = "default"

    config = AttrsConfig(var_int=9001)
    assert config.var_int == 9001
    assert config.var_bool is False
    assert config.var_str == "custom"
