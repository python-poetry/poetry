from __future__ import annotations

from tests.helpers import flatten_dict


def test_flatten_dict() -> None:
    orig_dict = {
        "a": 1,
        "b": 2,
        "c": {
            "x": 8,
            "y": 9,
        },
    }

    flattened_dict = {
        "a": 1,
        "b": 2,
        "c:x": 8,
        "c:y": 9,
    }

    assert flattened_dict == flatten_dict(orig_dict, delimiter=":")
