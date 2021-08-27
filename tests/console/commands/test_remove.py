<<<<<<< HEAD
from typing import TYPE_CHECKING

=======
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
import pytest
import tomlkit

from poetry.core.packages.package import Package
<<<<<<< HEAD

from poetry.factory import Factory


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.repositories import Repository
    from tests.helpers import PoetryTestApplication
    from tests.helpers import TestRepository
    from tests.types import CommandTesterFactory


@pytest.fixture()
def tester(command_tester_factory: "CommandTesterFactory") -> "CommandTester":
=======
from poetry.factory import Factory


@pytest.fixture()
def tester(command_tester_factory):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return command_tester_factory("remove")


def test_remove_without_specific_group_removes_from_all_groups(
<<<<<<< HEAD
    tester: "CommandTester",
    app: "PoetryTestApplication",
    repo: "TestRepository",
    command_tester_factory: "CommandTesterFactory",
    installed: "Repository",
=======
    tester, app, repo, command_tester_factory, installed
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    """
    Removing without specifying a group removes packages from all groups.
    """
    installed.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("baz", "1.0.0"))

    content = app.poetry.file.read()

    groups_content = tomlkit.parse(
        """\
[tool.poetry.group.bar.dependencies]
foo = "^2.0.0"
baz = "^1.0.0"

"""
    )
    content["tool"]["poetry"]["dependencies"]["foo"] = "^2.0.0"
    content["tool"]["poetry"].value._insert_after(
        "dependencies", "group", groups_content["tool"]["poetry"]["group"]
    )
    app.poetry.file.write(content)

    app.poetry.package.add_dependency(Factory.create_dependency("foo", "^2.0.0"))
    app.poetry.package.add_dependency(
        Factory.create_dependency("foo", "^2.0.0", groups=["bar"])
    )
    app.poetry.package.add_dependency(
        Factory.create_dependency("baz", "^1.0.0", groups=["bar"])
    )

    tester.execute("foo")

    content = app.poetry.file.read()["tool"]["poetry"]
    assert "foo" not in content["dependencies"]
    assert "foo" not in content["group"]["bar"]["dependencies"]
    assert "baz" in content["group"]["bar"]["dependencies"]

    expected = """\

[tool.poetry.group.bar.dependencies]
baz = "^1.0.0"

"""

    assert expected in content.as_string()


def test_remove_without_specific_group_removes_from_specific_groups(
<<<<<<< HEAD
    tester: "CommandTester",
    app: "PoetryTestApplication",
    repo: "TestRepository",
    command_tester_factory: "CommandTesterFactory",
    installed: "Repository",
=======
    tester, app, repo, command_tester_factory, installed
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    """
    Removing with a specific group given removes packages only from this group.
    """
    installed.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("baz", "1.0.0"))

    content = app.poetry.file.read()

    groups_content = tomlkit.parse(
        """\
[tool.poetry.group.bar.dependencies]
foo = "^2.0.0"
baz = "^1.0.0"

"""
    )
    content["tool"]["poetry"]["dependencies"]["foo"] = "^2.0.0"
    content["tool"]["poetry"].value._insert_after(
        "dependencies", "group", groups_content["tool"]["poetry"]["group"]
    )
    app.poetry.file.write(content)

    app.poetry.package.add_dependency(Factory.create_dependency("foo", "^2.0.0"))
    app.poetry.package.add_dependency(
        Factory.create_dependency("foo", "^2.0.0", groups=["bar"])
    )
    app.poetry.package.add_dependency(
        Factory.create_dependency("baz", "^1.0.0", groups=["bar"])
    )

    tester.execute("foo --group bar")

    content = app.poetry.file.read()["tool"]["poetry"]
    assert "foo" in content["dependencies"]
    assert "foo" not in content["group"]["bar"]["dependencies"]
    assert "baz" in content["group"]["bar"]["dependencies"]

    expected = """\

[tool.poetry.group.bar.dependencies]
baz = "^1.0.0"

"""

    assert expected in content.as_string()


def test_remove_does_not_live_empty_groups(
<<<<<<< HEAD
    tester: "CommandTester",
    app: "PoetryTestApplication",
    repo: "TestRepository",
    command_tester_factory: "CommandTesterFactory",
    installed: "Repository",
=======
    tester, app, repo, command_tester_factory, installed
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    """
    Empty groups are automatically discarded after package removal.
    """
    installed.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("baz", "1.0.0"))

    content = app.poetry.file.read()

    groups_content = tomlkit.parse(
        """\
[tool.poetry.group.bar.dependencies]
foo = "^2.0.0"
baz = "^1.0.0"

"""
    )
    content["tool"]["poetry"]["dependencies"]["foo"] = "^2.0.0"
    content["tool"]["poetry"].value._insert_after(
        "dependencies", "group", groups_content["tool"]["poetry"]["group"]
    )
    app.poetry.file.write(content)

    app.poetry.package.add_dependency(Factory.create_dependency("foo", "^2.0.0"))
    app.poetry.package.add_dependency(
        Factory.create_dependency("foo", "^2.0.0", groups=["bar"])
    )
    app.poetry.package.add_dependency(
        Factory.create_dependency("baz", "^1.0.0", groups=["bar"])
    )

    tester.execute("foo baz --group bar")

    content = app.poetry.file.read()["tool"]["poetry"]
    assert "foo" in content["dependencies"]
    assert "foo" not in content["group"]["bar"]["dependencies"]
    assert "baz" not in content["group"]["bar"]["dependencies"]
    assert "[tool.poetry.group.bar]" not in content.as_string()
    assert "[tool.poetry.group]" not in content.as_string()


def test_remove_command_should_not_write_changes_upon_installer_errors(
<<<<<<< HEAD
    tester: "CommandTester",
    app: "PoetryTestApplication",
    repo: "TestRepository",
    command_tester_factory: "CommandTesterFactory",
    mocker: "MockerFixture",
=======
    tester, app, repo, command_tester_factory, mocker
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    repo.add_package(Package("foo", "2.0.0"))

    command_tester_factory("add").execute("foo")

    mocker.patch("poetry.installation.installer.Installer.run", return_value=1)

    original_content = app.poetry.file.read().as_string()

    tester.execute("foo")

    assert app.poetry.file.read().as_string() == original_content
