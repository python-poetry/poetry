from __future__ import annotations

import pytest

from packaging.tags import Tag

from poetry.utils.env import MockEnv
from poetry.utils.wheel import Wheel


@pytest.mark.parametrize(
    ("filename", "supported_tags", "expected"),
    [
        ("demo-1.0.0-py3-none-any.whl", [Tag("py3", "none", "any")], True),
        ("demo-1.0.0-cp312-cp312-win_amd64.whl", [Tag("py3", "none", "any")], False),
        ("demo-1.0.0-py3-none-any.whl", [], False),
        (
            "demo-1.0.0-py3-none-any.whl",
            [Tag("cp310", "none", "any"), Tag("py3", "none", "any")],
            True,
        ),
    ],
)
def test_wheel_is_supported_by_environment(
    filename: str, supported_tags: list[Tag], expected: bool
) -> None:
    env = MockEnv(supported_tags=supported_tags)

    assert Wheel(filename).is_supported_by_environment(env) is expected


def test_env_supported_tags_set_is_cached() -> None:
    env = MockEnv(supported_tags=[Tag("py3", "none", "any")])

    assert env.supported_tags_set == set(env.supported_tags)
    assert env.supported_tags_set is env.supported_tags_set
