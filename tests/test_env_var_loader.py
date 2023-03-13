from minimal_configclasses import EnvVarLoader


class ConfigClass:
    var_int: int
    var_float: float
    var_str: str
    var_bool: bool
    var_list: list
    var_tuple: tuple
    var_dict: dict


def test_envvarloader_single_layer_namespace(monkeypatch):
    """Test that environment variable loader works with single namespace layer."""
    loader = EnvVarLoader(["testtool"])

    env_var_namespace = "TESTTOOL"
    monkeypatch.setenv(f"{env_var_namespace}_VAR_INT", "0")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_FLOAT", "0.5")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_STR", "zero")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_BOOL", "false")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_LIST", "['zero', 'one', 'two']")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_TUPLE", "['zero', 'one', 'two']")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_DICT", "{zero = 0, one = 1, two = 2}")

    assert loader(ConfigClass) == {
        "var_int": 0,
        "var_float": 0.5,
        "var_str": "zero",
        "var_bool": False,
        "var_list": ["zero", "one", "two"],
        "var_tuple": ("zero", "one", "two"),
        "var_dict": {"zero": 0, "one": 1, "two": 2},
    }


def test_envvarloader_nested_namespace(monkeypatch):
    """Test that environment variable loader works with nested namespace."""
    env_var_namespace = "TESTTOOL_TESTTOOLSUB"
    loader = EnvVarLoader(("testtool", "testtoolsub"))

    monkeypatch.setenv(f"{env_var_namespace}_VAR_INT", "0")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_FLOAT", "0.5")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_STR", "zero")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_BOOL", "false")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_LIST", "['zero', 'one', 'two']")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_TUPLE", "['zero', 'one', 'two']")
    monkeypatch.setenv(f"{env_var_namespace}_VAR_DICT", "{zero = 0, one = 1, two = 2}")

    assert loader(ConfigClass) == {
        "var_int": 0,
        "var_float": 0.5,
        "var_str": "zero",
        "var_bool": False,
        "var_list": ["zero", "one", "two"],
        "var_tuple": ("zero", "one", "two"),
        "var_dict": {"zero": 0, "one": 1, "two": 2},
    }
