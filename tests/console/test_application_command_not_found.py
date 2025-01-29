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
