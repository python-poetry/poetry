from __future__ import annotations

from typing import Any

import pytest

from poetry.config.config_source import drop_empty_config_category


@pytest.mark.parametrize(
    ["config_data", "expected"],
    [
        (
            {
                "category_a": {
                    "category_b": {
                        "category_c": {},
                    },
                },
                "system-git-client": True,
            },
            {"system-git-client": True},
        ),
        (
            {
                "category_a": {
                    "category_b": {
                        "category_c": {},
                        "category_d": {"some_config": True},
                    },
                },
                "system-git-client": True,
            },
            {
                "category_a": {
                    "category_b": {
                        "category_d": {"some_config": True},
                    }
                },
                "system-git-client": True,
            },
        ),
    ],
)
def test_drop_empty_config_category(
    config_data: dict[Any, Any], expected: dict[Any, Any]
) -> None:
    assert (
        drop_empty_config_category(
            keys=["category_a", "category_b", "category_c"], config=config_data
        )
        == expected
    )
