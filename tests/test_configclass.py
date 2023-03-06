import dataclasses
import os
from pathlib import Path

import attrs
import pydantic
import pytest
import tomli_w

from minimal_configclasses import configclass

TOOL_NAME = "testtool"


@pytest.fixture
def config_file_data():
    return {"var_int": 10, "var_str": "from_file"}


@pytest.fixture
def env_vars(monkeypatch):
    monkeypatch.setenv(f"{TOOL_NAME.upper()}_VAR_BOOL", "true")
    monkeypatch.setenv(f"{TOOL_NAME.upper()}_VAR_STR", "from_env")


@pytest.fixture
def pyproject_toml_file(config_file_data, tmp_path):
    payload = {"tool": {TOOL_NAME: config_file_data}}
    with (tmp_path / "pyproject.toml").open("wb") as fp:
        tomli_w.dump(payload, fp)

    orig_cwd = Path.cwd()
    os.chdir(tmp_path)
    yield
    os.chdir(orig_cwd)


def test_configclass_dataclass_pyproject_toml(pyproject_toml_file):
    @configclass(TOOL_NAME)
    @dataclasses.dataclass
    class DataClassConfig:
        var_int: int = 0
        var_bool: bool = False
        var_str: str = "default"

    config = DataClassConfig()
    assert config.var_int == 10
    assert config.var_bool is False
    assert config.var_str == "from_file"

    config = DataClassConfig(var_int=9001)
    assert config.var_int == 9001
    assert config.var_bool is False
    assert config.var_str == "from_file"


def test_configclass_dataclass_env_var_pyproject_toml(env_vars, pyproject_toml_file):
    @configclass(TOOL_NAME)
    @dataclasses.dataclass
    class DataClassConfig:
        var_int: int = 0
        var_bool: bool = False
        var_str: str = "default"

    config = DataClassConfig()
    assert config.var_int == 10
    assert config.var_bool is True
    assert config.var_str == "from_env"

    config = DataClassConfig(var_int=9001, var_bool=False)
    assert config.var_int == 9001
    assert config.var_bool is False
    assert config.var_str == "from_env"


def test_configclass_pydantic_pyproject_toml(pyproject_toml_file):
    @configclass(TOOL_NAME)
    class PydanticConfig(pydantic.BaseModel):
        var_int: int = 0
        var_bool: bool = False
        var_str: str = "default"

    config = PydanticConfig()
    assert config.var_int == 10
    assert config.var_bool is False
    assert config.var_str == "from_file"

    config = PydanticConfig(var_int=9001)
    assert config.var_int == 9001
    assert config.var_bool is False
    assert config.var_str == "from_file"


def test_configclass_attrs_pyproject_toml(pyproject_toml_file):
    @configclass(TOOL_NAME)
    @attrs.define
    class AttrsConfig:
        var_int: int = 0
        var_bool: bool = False
        var_str: str = "default"

    config = AttrsConfig()
    assert config.var_int == 10
    assert config.var_bool is False
    assert config.var_str == "from_file"

    config = AttrsConfig(var_int=9001)
    assert config.var_int == 9001
    assert config.var_bool is False
    assert config.var_str == "from_file"
