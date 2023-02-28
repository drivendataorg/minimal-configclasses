import os
from pathlib import Path

import pytest
import tomli_w

from minimal_configclasses import EnvVarLoader, TomlFileLoader

TOOLNAMES = ["testtool", "testtoolsub"]


class ConfigClass:
    var_int: int
    var_float: float
    var_str: str
    var_bytes: bytes
    var_bool: bool
    var_list: list
    var_dict: dict


def test_envvarloader_singlename(monkeypatch):
    """Test that environment variable loader works under basic use with a single name."""
    tool_name = TOOLNAMES[0]
    loader = EnvVarLoader(names=[tool_name])

    env_var_namespace = tool_name.upper()
    monkeypatch.setenv(f"{env_var_namespace}_VAR_INT", "0")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_FLOAT", "0.5")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_STR", "zero")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_BYTES", "zero")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_BOOL", "false")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_LIST", "['zero', 'one', 'two']")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_DICT", "{zero = 0, one = 1, two = 2}")

    assert next(loader(ConfigClass))[0] == {
        "var_int": 0,
        "var_float": 0.5,
        "var_str": "zero",
        "var_bytes": b"zero",
        "var_bool": False,
        "var_list": ["zero", "one", "two"],
        "var_dict": {"zero": 0, "one": 1, "two": 2},
    }


def test_envvarloader_deepernames(monkeypatch):
    """Test that environment variable loader works under a name path."""
    env_var_namespace = "_".join(t.upper() for t in TOOLNAMES)
    loader = EnvVarLoader(names=TOOLNAMES)

    monkeypatch.setenv(f"{env_var_namespace}_VAR_INT", "0")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_FLOAT", "0.5")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_STR", "zero")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_BYTES", "zero")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_BOOL", "false")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_LIST", "['zero', 'one', 'two']")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_DICT", "{zero = 0, one = 1, two = 2}")

    assert next(loader(ConfigClass))[0] == {
        "var_int": 0,
        "var_float": 0.5,
        "var_str": "zero",
        "var_bytes": b"zero",
        "var_bool": False,
        "var_list": ["zero", "one", "two"],
        "var_dict": {"zero": 0, "one": 1, "two": 2},
    }


@pytest.fixture
def working_dir(tmp_path):
    working_dir = tmp_path / "proj_root" / "working_dir"
    working_dir.mkdir(parents=True)
    orig_wd = Path.cwd()
    os.chdir(working_dir)
    yield working_dir
    os.chdir(orig_wd)


def test_tomlfileloader_singlename(tmp_path, working_dir, monkeypatch):
    """Test that TomlFileLoader works and discovers data in all expected files."""
    proj_root = working_dir.parent
    home = Path(tmp_path) / "home"
    home.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    xdg_config_home = home / ".config"
    xdg_config_home.mkdir(parents=True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config_home))

    # Reverse order of precedence
    paths = [
        home / f".{TOOLNAMES[0]}.toml",
        home / f"{TOOLNAMES[0]}.toml",
        xdg_config_home / f".{TOOLNAMES[0]}.toml",
        xdg_config_home / f"{TOOLNAMES[0]}.toml",
        proj_root / f".{TOOLNAMES[0]}.toml",
        proj_root / f"{TOOLNAMES[0]}.toml",
        proj_root / "pyproject.toml",
        working_dir / f".{TOOLNAMES[0]}.toml",
        working_dir / f"{TOOLNAMES[0]}.toml",
        working_dir / "pyproject.toml",
    ]

    loader = TomlFileLoader(TOOLNAMES[:1])

    class ConfigClass:
        var_int: int

    for i, path in enumerate(paths):
        data = {"var_int": i}
        if path.name == "pyproject.toml":
            data = {"tool": {TOOLNAMES[0]: data}}
        with path.open("wb") as fp:
            tomli_w.dump(data, fp)

        loader_gen = loader(ConfigClass)
        for j in range(i + 1):
            assert next(loader_gen)[0] == {"var_int": i - j}


def test_tomlfileloader_deepernames(tmp_path, working_dir, monkeypatch):
    """Test that TomlFileLoader works and discovers data in all expected files."""
    proj_root = working_dir.parent
    home = Path(tmp_path) / "home"
    home.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    xdg_config_home = home / ".config"
    xdg_config_home.mkdir(parents=True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config_home))

    # Reverse order of precedence
    paths = [
        home / f".{TOOLNAMES[0]}.toml",
        home / f"{TOOLNAMES[0]}.toml",
        xdg_config_home / f".{TOOLNAMES[0]}.toml",
        xdg_config_home / f"{TOOLNAMES[0]}.toml",
        proj_root / f".{TOOLNAMES[0]}.toml",
        proj_root / f"{TOOLNAMES[0]}.toml",
        proj_root / "pyproject.toml",
        working_dir / f".{TOOLNAMES[0]}.toml",
        working_dir / f"{TOOLNAMES[0]}.toml",
        working_dir / "pyproject.toml",
    ]

    loader = TomlFileLoader(TOOLNAMES)

    class ConfigClass:
        var_int: int

    for i, path in enumerate(paths):
        data = {"var_int": i}
        for key in reversed(TOOLNAMES):
            data = {key: data}
        if path.name == "pyproject.toml":
            data = {"tool": data}
        else:
            data = data[TOOLNAMES[0]]
        with path.open("wb") as fp:
            tomli_w.dump(data, fp)

        loader_gen = loader(ConfigClass)
        for j in range(i + 1):
            assert next(loader_gen)[0] == {"var_int": i - j}
