from minimal_configclasses import last_seen_wins_merge_resolver


def test_merge_all_resolver():
    source_data = [
        lambda _: {"a": 2, "b": 2, "c": 2},
        lambda _: {"a": 1, "b": 1},
        lambda _: {"a": 0},
    ]

    class ConfigClass:
        pass

    assert last_seen_wins_merge_resolver(source_data, ConfigClass) == {"a": 0, "b": 1, "c": 2}
