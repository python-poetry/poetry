import re

from typing import TYPE_CHECKING

from cleo.testers.application_tester import ApplicationTester
from entrypoints import EntryPoint

from poetry.console.application import Application
from poetry.console.commands.command import Command
from poetry.plugins.application_plugin import ApplicationPlugin


if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class FooCommand(Command):
    name = "foo"

    description = "Foo Command"

    def handle(self) -> int:
        self.line("foo called")

        return 0


class AddCommandPlugin(ApplicationPlugin):
    def activate(self, application: Application) -> None:
        application.command_loader.register_factory("foo", lambda: FooCommand())


def test_application_with_plugins(mocker: "MockerFixture"):
    mocker.patch(
        "entrypoints.get_group_all",
        return_value=[
            EntryPoint(
                "my-plugin", "tests.console.test_application", "AddCommandPlugin"
            )
        ],
    )

    app = Application()

    tester = ApplicationTester(app)
    tester.execute("")

    assert re.search(r"\s+foo\s+Foo Command", tester.io.fetch_output()) is not None
    assert 0 == tester.status_code


def test_application_with_plugins_disabled(mocker: "MockerFixture"):
    mocker.patch(
        "entrypoints.get_group_all",
        return_value=[
            EntryPoint(
                "my-plugin", "tests.console.test_application", "AddCommandPlugin"
            )
        ],
    )

    app = Application()

    tester = ApplicationTester(app)
    tester.execute("--no-plugins")

    assert re.search(r"\s+foo\s+Foo Command", tester.io.fetch_output()) is None
    assert 0 == tester.status_code


def test_application_execute_plugin_command(mocker: "MockerFixture"):
    mocker.patch(
        "entrypoints.get_group_all",
        return_value=[
            EntryPoint(
                "my-plugin", "tests.console.test_application", "AddCommandPlugin"
            )
        ],
    )

    app = Application()

    tester = ApplicationTester(app)
    tester.execute("foo")

    assert "foo called\n" == tester.io.fetch_output()
    assert 0 == tester.status_code


def test_application_execute_plugin_command_with_plugins_disabled(
    mocker: "MockerFixture",
):
    mocker.patch(
        "entrypoints.get_group_all",
        return_value=[
            EntryPoint(
                "my-plugin", "tests.console.test_application", "AddCommandPlugin"
            )
        ],
    )

    app = Application()

    tester = ApplicationTester(app)
    tester.execute("foo --no-plugins")

    assert "" == tester.io.fetch_output()
    assert '\nThe command "foo" does not exist.\n' == tester.io.fetch_error()
    assert 1 == tester.status_code
