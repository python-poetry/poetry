from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cleo.testers.application_tester import ApplicationTester

from poetry.console.application import Application


if TYPE_CHECKING:
    from tests.types import CommandFactory


@pytest.fixture
def tester() -> ApplicationTester:
    return ApplicationTester(Application())


@pytest.mark.parametrize(
    ("command", "suggested"),
    [
        ("x", None),
        ("en", ["env activate", "env info", "env list", "env remove", "env use"]),
        ("sou", ["source add", "source remove", "source show"]),
    ],
)
def test_application_command_not_found_messages(
    command: str,
    suggested: list[str] | None,
    tester: ApplicationTester,
    command_factory: CommandFactory,
) -> None:
    tester.execute(f"{command}")
    assert tester.status_code != 0

    stderr = tester.io.fetch_error()
    assert f"The requested command {command} does not exist." in stderr

    if suggested is None:
        assert "Did you mean one of these perhaps?" not in stderr
    else:
        for suggestion in suggested:
            assert suggestion in stderr


@pytest.mark.parametrize(
    "namespace",
    ["cache", "debug", "env", "self", "source"],
)
def test_application_namespaced_command_not_found_messages(
    namespace: str,
    tester: ApplicationTester,
    command_factory: CommandFactory,
) -> None:
    tester.execute(f"{namespace} xxx")
    assert tester.status_code != 0

    stderr = tester.io.fetch_error()
    assert (
        f"The requested command does not exist in the {namespace} namespace." in stderr
    )
