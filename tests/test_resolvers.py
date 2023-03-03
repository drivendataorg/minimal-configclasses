from minimal_configclasses import (
    EnvVarLoader,
    TomlFileLoader,
    first_only_resolver,
    merge_all_resolver,
    merge_env_var_and_first_toml_resolver,
)


def test_merge_all_resolver():
    source_data = [
        ({"a": 0}, {}),
        ({"a": 1, "b": 1}, {}),
        ({"a": 2, "b": 2, "c": 2}, {}),
    ]

    class ConfigClass:
        a: int
        b: int
        c: int

    assert merge_all_resolver(source_data, ConfigClass) == {"a": 0, "b": 1, "c": 2}


def test_first_only_resolver():
    source_data = [
        ({"a": 0}, {}),
        ({"a": 1, "b": 1}, {}),
        ({"a": 2, "b": 2, "c": 2}, {}),
    ]

    class ConfigClass:
        a: int
        b: int
        c: int

    assert first_only_resolver(source_data, ConfigClass) == {"a": 0}


def test_merge_env_var_and_first_toml_resolver():
    env_var_loader = EnvVarLoader(names=["foo"])
    toml_file_loader = TomlFileLoader(names=["foo"])
    source_data = [
        ({"a": 0}, {"loader": env_var_loader}),
        ({"a": 1, "b": 1}, {"loader": toml_file_loader}),
        ({"a": 2, "b": 2, "c": 2}, {"loader": toml_file_loader}),
    ]

    class ConfigClass:
        a: int
        b: int
        c: int

    assert merge_env_var_and_first_toml_resolver(source_data, ConfigClass) == {"a": 0, "b": 1}
