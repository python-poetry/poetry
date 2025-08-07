from __future__ import annotations

from tests.helpers import flatten_dict


def test_flatten_dict_simple() -> None:
    nested = {"a": {"b": {"c": 1}}, "d": 2}
    flat = flatten_dict(nested)
    expected = {"a.b.c": 1, "d": 2}
    assert flat == expected
