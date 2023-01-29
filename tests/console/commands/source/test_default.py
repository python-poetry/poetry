from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from poetry.config.source import Source
    from poetry.poetry import Poetry
    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(
    command_tester_factory: CommandTesterFactory, poetry_with_source: Poetry
) -> CommandTester:
    return command_tester_factory("source default", poetry=poetry_with_source)


def test_source_default_enabled_by_default(
    tester: CommandTester,
    source_existing: Source,
    source_default: Source,
    poetry_with_source: Poetry,
) -> None:
    tester.execute("")
    assert "enabled" in tester.io.fetch_output()
    poetry_with_source.pyproject.reload()
    assert "default-source-pypi" not in poetry_with_source.pyproject.poetry_config


@pytest.mark.parametrize("enable", [True, False])
def test_source_default_disable(
    tester: CommandTester,
    source_existing: Source,
    source_default: Source,
    poetry_with_source: Poetry,
    enable: bool,
) -> None:
    tester.execute("--enable-pypi" if enable else "--disable-pypi")
    poetry_with_source.pyproject.reload()
    assert poetry_with_source.pyproject.poetry_config["default-source-pypi"] is enable

    tester.execute("")
    output = tester.io.fetch_output()
    assert ("enabled" in output) is enable
    assert ("disabled" in output) is not enable
    poetry_with_source.pyproject.reload()
    assert poetry_with_source.pyproject.poetry_config["default-source-pypi"] is enable
