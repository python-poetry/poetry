from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from packaging.tags import Tag

from poetry.utils.env import MockEnv


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(
    command_tester_factory: CommandTesterFactory, mocker: MockerFixture
) -> CommandTester:
    env = MockEnv(path=Path("/prefix"))

    mocker.patch.object(
        env,
        "get_supported_tags",
        return_value=[
            Tag("cp312", "cp312", "manylinux_2_17_x86_64"),
            Tag("py3", "none", "any"),
        ],
    )

    return command_tester_factory("debug tags", environment=env)


def test_debug_tags_lists_supported_tags(tester: CommandTester) -> None:

    tester.execute()

    expected = "cp312-cp312-manylinux_2_17_x86_64\npy3-none-any\n"
    assert tester.io.fetch_output() == expected
