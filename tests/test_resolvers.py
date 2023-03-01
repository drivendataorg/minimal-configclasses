from minimal_configclasses import FirstOnlyResolver, MergeResolver


def test_mergeresolver():
    source_data = [
        ({"a": 0}, {}),
        ({"a": 1, "b": 1}, {}),
        ({"a": 2, "b": 2, "c": 2}, {}),
    ]

    class ConfigClass:
        a: int
        b: int
        c: int

    merge_all_resolver = MergeResolver()
    assert merge_all_resolver(iter(source_data), ConfigClass) == {"a": 0, "b": 1, "c": 2}

    merge_two_resolver = MergeResolver(2)
    assert merge_two_resolver(iter(source_data), ConfigClass) == {"a": 0, "b": 1}


def test_firstonlyresolver():
    source_data = [
        ({"a": 0}, {}),
        ({"a": 1, "b": 1}, {}),
        ({"a": 2, "b": 2, "c": 2}, {}),
    ]

    class ConfigClass:
        a: int
        b: int
        c: int

    first_only_resolver = FirstOnlyResolver()
    assert first_only_resolver(iter(source_data), ConfigClass) == {"a": 0}
