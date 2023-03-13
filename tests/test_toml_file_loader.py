import io
import os
from pathlib import Path
import platform
from textwrap import dedent
from types import SimpleNamespace

import pytest
import tomli_w

from minimal_configclasses import TomlFileLoader, load_toml
from tests.utils import (
    requires_macos,
    requires_not_macos,
    requires_not_windows,
    requires_windows,
    working_directory,
)

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


def test_named_files():
    """Test that TomlFileLoader produces expected named files."""
    # Default templates with single namespace part
    loader = TomlFileLoader(namespace=("mytool",))
    assert set(loader.named_files) == {"mytool.toml", ".mytool.toml"}

    # Default templates with many namespace parts
    loader = TomlFileLoader(namespace=("mytool0", "mytool1"))
    assert set(loader.named_files) == {"mytool0.toml", ".mytool0.toml"}

    # Different template
    loader = TomlFileLoader(namespace=("mytool",), named_file_templates=("_{}.toml",))
    assert set(loader.named_files) == {"_mytool.toml"}

    # Empty templates
    loader = TomlFileLoader(namespace=("mytool",), named_file_templates=())
    assert set(loader.named_files) == set()


def test_check_pyproject_toml():
    loader = TomlFileLoader(namespace=("mytool",))
    assert "pyproject.toml" in {path.name for path in loader.paths_to_check}

    loader = TomlFileLoader(namespace=("mytool",), check_pyproject_toml=False)
    assert "pyproject.toml" not in {path.name for path in loader.paths_to_check}


@pytest.fixture
def project_tree(tmp_path):
    """Fixture that creates a project tree in a temp directory."""
    project_tree = SimpleNamespace()
    project_tree.proj_parent = tmp_path / "proj_parent"
    project_tree.proj_root = project_tree.proj_parent / "proj_root"
    project_tree.proj_subdir = project_tree.proj_root / "proj_subdir"
    project_tree.proj_subdir.mkdir(parents=True)
    yield project_tree


def test_project_files(project_tree):
    """Test that TomlFileLoader checks project files as expected."""
    loader = TomlFileLoader(
        namespace=("mytool",),
        check_xdg_config_home_dir=False,
        check_home_dir=False,
        check_macos_application_support_dir=False,
        check_windows_appdata_dir=False,
    )
    files_to_check = ["pyproject.toml", "mytool.toml", ".mytool.toml"]

    # No git repository, should check everything down to system root
    expected_dirs = [project_tree.proj_subdir] + list(project_tree.proj_subdir.absolute().parents)
    assert expected_dirs[-1] == Path("/")
    expected_files = [d / f for d in expected_dirs for f in files_to_check]
    with working_directory(project_tree.proj_subdir):
        assert list(loader.paths_to_check) == expected_files

    # Add a git repository to proj_root
    (project_tree.proj_root / ".git").mkdir()
    with working_directory(project_tree.proj_subdir):
        assert list(loader.paths_to_check) == [
            d / f
            for d in [project_tree.proj_subdir, project_tree.proj_root]
            for f in files_to_check
        ]
    with working_directory(project_tree.proj_root):
        assert list(loader.paths_to_check) == [project_tree.proj_root / f for f in files_to_check]

    # Loader with stop_on_repo_root=False does not stop
    loader = TomlFileLoader(
        namespace=("mytool",),
        stop_on_repo_root=False,
        check_xdg_config_home_dir=False,
        check_home_dir=False,
        check_macos_application_support_dir=False,
        check_windows_appdata_dir=False,
    )
    with working_directory(project_tree.proj_subdir):
        assert list(loader.paths_to_check) == expected_files

    # Loader with search_ancestors=False stops
    loader = TomlFileLoader(
        namespace=("mytool",),
        search_ancestor_dirs=False,
        check_xdg_config_home_dir=False,
        check_home_dir=False,
        check_macos_application_support_dir=False,
        check_windows_appdata_dir=False,
    )
    with working_directory(project_tree.proj_subdir):
        assert list(loader.paths_to_check) == [
            project_tree.proj_subdir / f for f in files_to_check
        ]


@pytest.fixture
def home_dir(tmp_path, monkeypatch):
    """Fixture that sets the home directory to a temp directory."""
    home_dir = tmp_path / "home"
    # We expect normal systems to have this env var set
    assert os.getenv("HOME")
    monkeypatch.setenv("HOME", str(home_dir))
    return home_dir


def test_check_home_dir(home_dir):
    """Test that checking home directory works."""
    assert os.getenv("HOME")
    loader = TomlFileLoader(namespace=("mytool",))
    paths_to_check = set(loader.paths_to_check)
    for named_file in loader.named_files:
        assert home_dir / named_file in paths_to_check

    # check_home_dir is False
    loader = TomlFileLoader(namespace=("mytool",), check_home_dir=False)
    paths_to_check = set(loader.paths_to_check)
    for named_file in loader.named_files:
        assert home_dir / named_file not in paths_to_check


@pytest.fixture
def xdg_config_home_dir(tmp_path, monkeypatch):
    """Fixture that sets the XDG config home directory to a temp directory."""
    xdg_config_home_dir = tmp_path / "xdg_config_home"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config_home_dir))
    return xdg_config_home_dir


def test_check_xdg_config_home_dir(xdg_config_home_dir):
    """Test that XDG_CONFIG_HOME env var is respected."""
    assert os.getenv("XDG_CONFIG_HOME")
    loader = TomlFileLoader(namespace=("mytool",))
    paths_to_check = set(loader.paths_to_check)
    for named_file in loader.named_files:
        assert xdg_config_home_dir / named_file in paths_to_check

    # check_xdg_config_home_dir is False
    loader = TomlFileLoader(namespace=("mytool",), check_xdg_config_home_dir=False)
    paths_to_check = set(loader.paths_to_check)
    for named_file in loader.named_files:
        assert xdg_config_home_dir / named_file not in paths_to_check


def test_check_xdg_config_home_dir_no_env_var(home_dir):
    """Test that default location for XDG config home is checked if XDG_CONFIG_HOME is not set."""
    assert not os.getenv("XDG_CONFIG_HOME")
    loader = TomlFileLoader(namespace=("mytool",))
    paths_to_check = set(loader.paths_to_check)
    for named_file in loader.named_files:
        assert home_dir / ".config" / named_file in paths_to_check


@requires_macos
def test_check_macos_application_support_dir(home_dir):
    """Test that macOS application support directory works."""
    loader = TomlFileLoader(namespace=("mytool",))
    paths_to_check = set(loader.paths_to_check)
    for named_file in loader.named_files:
        assert home_dir / "Library" / "Application Support" / named_file in paths_to_check

    # check_macos_application_support_dir = False
    loader = TomlFileLoader(namespace=("mytool",), check_macos_application_support_dir=False)
    paths_to_check = set(loader.paths_to_check)
    for named_file in loader.named_files:
        assert home_dir / "Library" / "Application Support" / named_file not in paths_to_check


@requires_not_macos
def test_check_macos_application_support_dir_not_macos(home_dir):
    """Test that default location for Windows AppData is checked if APPDATA is not set."""
    loader = TomlFileLoader(namespace=("mytool",))
    paths_to_check = set(loader.paths_to_check)
    for named_file in loader.named_files:
        assert home_dir / "Library" / "Application Support" / named_file not in paths_to_check


@pytest.fixture
def win_appdata_dir(tmp_path, monkeypatch):
    """Fixture that sets the Windows AppData directory to a temp directory."""
    win_appdata_dir = tmp_path / "win_appdata"
    # We expect normal Windows systems to have this env var set
    if platform.system() == "Windows":
        assert os.getenv("APPDATA")
    monkeypatch.setenv("APPDATA", str(win_appdata_dir))
    return win_appdata_dir


@requires_windows
def test_check_windows_appdata_dir(win_appdata_dir):
    """Test that Windows AppData directory works and APPDATA env var is respected."""
    assert os.getenv("APPDATA")
    loader = TomlFileLoader(namespace=("mytool",))
    paths_to_check = set(loader.paths_to_check)
    for named_file in loader.named_files:
        assert win_appdata_dir / named_file in paths_to_check

    # check_windows_appdata_dir = False
    loader = TomlFileLoader(namespace=("mytool",), check_windows_appdata_dir=False)
    paths_to_check = set(loader.paths_to_check)
    for named_file in loader.named_files:
        assert win_appdata_dir / named_file not in paths_to_check


@requires_windows
def test_check_windows_appdata_dir_no_env_var(home_dir):
    """Test that default location for Windows AppData is checked if APPDATA is not set."""
    assert not os.getenv("APPDATA")
    loader = TomlFileLoader(namespace=("mytool",))
    paths_to_check = set(loader.paths_to_check)
    for named_file in loader.named_files:
        assert home_dir / "AppData" / "Roaming" / named_file in paths_to_check


@requires_not_windows
def test_check_windows_appdata_dir_not_windows(win_appdata_dir):
    """Test that Windows AppData is not checked if not on Windows."""
    assert os.getenv("APPDATA")
    loader = TomlFileLoader(namespace=("mytool",))
    paths_to_check = set(loader.paths_to_check)
    for named_file in loader.named_files:
        assert win_appdata_dir / named_file not in paths_to_check


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
