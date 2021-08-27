import re

<<<<<<< HEAD
from typing import TYPE_CHECKING

=======
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
from cleo.testers.application_tester import ApplicationTester
from entrypoints import EntryPoint

from poetry.console.application import Application
from poetry.console.commands.command import Command
from poetry.plugins.application_plugin import ApplicationPlugin


<<<<<<< HEAD
if TYPE_CHECKING:
    from pytest_mock import MockerFixture


=======
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
class FooCommand(Command):
    name = "foo"

    description = "Foo Command"

<<<<<<< HEAD
    def handle(self) -> int:
=======
    def handle(self):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        self.line("foo called")

        return 0


class AddCommandPlugin(ApplicationPlugin):
<<<<<<< HEAD
    def activate(self, application: Application) -> None:
        application.command_loader.register_factory("foo", lambda: FooCommand())


def test_application_with_plugins(mocker: "MockerFixture"):
=======
    def activate(self, application: Application):
        application.command_loader.register_factory("foo", lambda: FooCommand())


def test_application_with_plugins(mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
<<<<<<< HEAD
    assert tester.status_code == 0


def test_application_with_plugins_disabled(mocker: "MockerFixture"):
=======
    assert 0 == tester.status_code


def test_application_with_plugins_disabled(mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
<<<<<<< HEAD
    assert tester.status_code == 0


def test_application_execute_plugin_command(mocker: "MockerFixture"):
=======
    assert 0 == tester.status_code


def test_application_execute_plugin_command(mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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

<<<<<<< HEAD
    assert tester.io.fetch_output() == "foo called\n"
    assert tester.status_code == 0


def test_application_execute_plugin_command_with_plugins_disabled(
    mocker: "MockerFixture",
):
=======
    assert "foo called\n" == tester.io.fetch_output()
    assert 0 == tester.status_code


def test_application_execute_plugin_command_with_plugins_disabled(mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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

<<<<<<< HEAD
    assert tester.io.fetch_output() == ""
    assert tester.io.fetch_error() == '\nThe command "foo" does not exist.\n'
    assert tester.status_code == 1
=======
    assert "" == tester.io.fetch_output()
    assert '\nThe command "foo" does not exist.\n' == tester.io.fetch_error()
    assert 1 == tester.status_code
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
