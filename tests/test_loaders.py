import io
import os
from pathlib import Path
from textwrap import dedent

import pytest
import tomli_w

from minimal_configclasses import EnvVarLoader, TomlFileLoader, load_toml

TOOLNAMES = ["testtool", "testtoolsub"]


def test_load_toml(tmp_path):
    # Root namespace
    toml_data = dedent(
        """\
        var_root = 0
        """
    )
    toml_file = tmp_path / "data.toml"
    toml_file.write_text(toml_data)
    assert load_toml(toml_file, ()) == {"var_root": 0}

    # With namespace
    toml_data = dedent(
        """\
        var_root = 0

        [tool.mytool]
        var_mytool = 1

        [ns0.ns1.ns2]
        var_nested = 2
        ns3 = {var_inline = 3}

        [tool.emptyns]
        """
    )
    toml_file = tmp_path / "data.toml"
    toml_file.write_text(toml_data)
    assert load_toml(toml_file, ("tool", "mytool")) == {"var_mytool": 1}
    assert load_toml(toml_file, ("ns0", "ns1", "ns2")) == {
        "var_nested": 2,
        "ns3": {"var_inline": 3},
    }
    assert load_toml(toml_file, ("ns0", "ns1", "ns2", "ns3")) == {"var_inline": 3}
    assert load_toml(toml_file, ("tool", "emptyns")) == {}
    with pytest.raises(KeyError):
        load_toml(toml_file, ("tool", "notthere"))
    with pytest.raises(TypeError):
        load_toml(toml_file, ("var_root",))

    # Empty file
    toml_data = ""
    toml_file = tmp_path / "data.toml"
    toml_file.write_text(toml_data)
    assert load_toml(toml_file, ()) == {}
    with pytest.raises(KeyError):
        load_toml(toml_file, ("ns"))


class ConfigClass:
    var_int: int
    var_float: float
    var_str: str
    var_bytes: bytes
    var_bool: bool
    var_list: list
    var_dict: dict


def test_envvarloader_single_layer_namespace(monkeypatch):
    """Test that environment variable loader works with single namespace layer."""
    loader = EnvVarLoader(["testtool"])

    env_var_namespace = "TESTTOOL"
    monkeypatch.setenv(f"{env_var_namespace}_VAR_INT", "0")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_FLOAT", "0.5")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_STR", "zero")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_BYTES", "zero")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_BOOL", "false")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_LIST", "['zero', 'one', 'two']")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_DICT", "{zero = 0, one = 1, two = 2}")

    assert loader(ConfigClass) == {
        "var_int": 0,
        "var_float": 0.5,
        "var_str": "zero",
        "var_bytes": b"zero",
        "var_bool": False,
        "var_list": ["zero", "one", "two"],
        "var_dict": {"zero": 0, "one": 1, "two": 2},
    }


def test_envvarloader_nested_namespace(monkeypatch):
    """Test that environment variable loader works with nested namespace."""
    env_var_namespace = "TESTTOOL_TESTTOOLSUB"
    loader = EnvVarLoader(("testtool", "testtoolsub"))

    monkeypatch.setenv(f"{env_var_namespace}_VAR_INT", "0")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_FLOAT", "0.5")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_STR", "zero")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_BYTES", "zero")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_BOOL", "false")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_LIST", "['zero', 'one', 'two']")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_DICT", "{zero = 0, one = 1, two = 2}")

    assert loader(ConfigClass) == {
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


# def test_tomlfileloader_singlename(tmp_path, working_dir, monkeypatch):
#     """Test that TomlFileLoader works and discovers data in all expected files."""
#     proj_root = working_dir.parent
#     home = Path(tmp_path) / "home"
#     home.mkdir(parents=True)
#     monkeypatch.setenv("HOME", str(home))
#     xdg_config_home = home / ".config"
#     xdg_config_home.mkdir(parents=True)
#     monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config_home))

#     # Reverse order of precedence
#     paths = [
#         home / f".{TOOLNAMES[0]}.toml",
#         home / f"{TOOLNAMES[0]}.toml",
#         xdg_config_home / f".{TOOLNAMES[0]}.toml",
#         xdg_config_home / f"{TOOLNAMES[0]}.toml",
#         proj_root / f".{TOOLNAMES[0]}.toml",
#         proj_root / f"{TOOLNAMES[0]}.toml",
#         proj_root / "pyproject.toml",
#         working_dir / f".{TOOLNAMES[0]}.toml",
#         working_dir / f"{TOOLNAMES[0]}.toml",
#         working_dir / "pyproject.toml",
#     ]

#     loader = TomlFileLoader(TOOLNAMES[:1])

#     class ConfigClass:
#         var_int: int

#     for i, path in enumerate(paths):
#         data = {"var_int": i}
#         if path.name == "pyproject.toml":
#             data = {"tool": {TOOLNAMES[0]: data}}
#         with path.open("wb") as fp:
#             tomli_w.dump(data, fp)

#         loader_gen = loader(ConfigClass)
#         for j in range(i + 1):
#             assert next(loader_gen)[0] == {"var_int": i - j}


# def test_tomlfileloader_deepernames(tmp_path, working_dir, monkeypatch):
#     """Test that TomlFileLoader works and discovers data in all expected files."""
#     proj_root = working_dir.parent
#     home = Path(tmp_path) / "home"
#     home.mkdir(parents=True)
#     monkeypatch.setenv("HOME", str(home))
#     xdg_config_home = home / ".config"
#     xdg_config_home.mkdir(parents=True)
#     monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config_home))

#     # Reverse order of precedence
#     paths = [
#         home / f".{TOOLNAMES[0]}.toml",
#         home / f"{TOOLNAMES[0]}.toml",
#         xdg_config_home / f".{TOOLNAMES[0]}.toml",
#         xdg_config_home / f"{TOOLNAMES[0]}.toml",
#         proj_root / f".{TOOLNAMES[0]}.toml",
#         proj_root / f"{TOOLNAMES[0]}.toml",
#         proj_root / "pyproject.toml",
#         working_dir / f".{TOOLNAMES[0]}.toml",
#         working_dir / f"{TOOLNAMES[0]}.toml",
#         working_dir / "pyproject.toml",
#     ]

#     loader = TomlFileLoader(TOOLNAMES)

#     class ConfigClass:
#         var_int: int

#     for i, path in enumerate(paths):
#         data = {"var_int": i}
#         for key in reversed(TOOLNAMES):
#             data = {key: data}
#         if path.name == "pyproject.toml":
#             data = {"tool": data}
#         else:
#             data = data[TOOLNAMES[0]]
#         with path.open("wb") as fp:
#             tomli_w.dump(data, fp)

#         loader_gen = loader(ConfigClass)
#         for j in range(i + 1):
#             assert next(loader_gen)[0] == {"var_int": i - j}
