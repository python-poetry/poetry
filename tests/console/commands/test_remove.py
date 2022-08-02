from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import tomlkit

from poetry.core.packages.package import Package

from poetry.factory import Factory
from tests.helpers import get_package


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry
    from poetry.repositories import Repository
    from tests.helpers import PoetryTestApplication
    from tests.helpers import TestRepository
    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter
    from tests.types import ProjectFactory


@pytest.fixture
def poetry_with_up_to_date_lockfile(
    project_factory: ProjectFactory, fixture_dir: FixtureDirGetter
) -> Poetry:
    source = fixture_dir("up_to_date_lock")

    return project_factory(
        name="foobar",
        pyproject_content=(source / "pyproject.toml").read_text(encoding="utf-8"),
        poetry_lock_content=(source / "poetry.lock").read_text(encoding="utf-8"),
    )


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("remove")


def test_remove_without_specific_group_removes_from_all_groups(
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    command_tester_factory: CommandTesterFactory,
    installed: Repository,
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
    content["tool"]["poetry"]["group"] = groups_content["tool"]["poetry"]["group"]
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
    string_content = content.as_string()
    if "\r\n" in string_content:
        # consistent line endings
        expected = expected.replace("\n", "\r\n")

    assert expected in string_content


def test_remove_without_specific_group_removes_from_specific_groups(
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    command_tester_factory: CommandTesterFactory,
    installed: Repository,
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
    content["tool"]["poetry"]["group"] = groups_content["tool"]["poetry"]["group"]
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
    string_content = content.as_string()
    if "\r\n" in string_content:
        # consistent line endings
        expected = expected.replace("\n", "\r\n")

    assert expected in string_content


def test_remove_does_not_live_empty_groups(
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    command_tester_factory: CommandTesterFactory,
    installed: Repository,
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
    content["tool"]["poetry"]["group"] = groups_content["tool"]["poetry"]["group"]
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


def test_remove_canonicalized_named_removes_dependency_correctly(
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    command_tester_factory: CommandTesterFactory,
    installed: Repository,
):
    """
    Removing a dependency using a canonicalized named removes the dependency.
    """
    installed.add_package(Package("foo-bar", "2.0.0"))
    repo.add_package(Package("foo-bar", "2.0.0"))
    repo.add_package(Package("baz", "1.0.0"))

    content = app.poetry.file.read()

    groups_content = tomlkit.parse(
        """\
[tool.poetry.group.bar.dependencies]
foo-bar = "^2.0.0"
baz = "^1.0.0"

"""
    )
    content["tool"]["poetry"]["dependencies"]["foo-bar"] = "^2.0.0"
    content["tool"]["poetry"].value._insert_after(
        "dependencies", "group", groups_content["tool"]["poetry"]["group"]
    )
    app.poetry.file.write(content)

    app.poetry.package.add_dependency(Factory.create_dependency("foo-bar", "^2.0.0"))
    app.poetry.package.add_dependency(
        Factory.create_dependency("foo-bar", "^2.0.0", groups=["bar"])
    )
    app.poetry.package.add_dependency(
        Factory.create_dependency("baz", "^1.0.0", groups=["bar"])
    )

    tester.execute("Foo_Bar")

    content = app.poetry.file.read()["tool"]["poetry"]
    assert "foo-bar" not in content["dependencies"]
    assert "foo-bar" not in content["group"]["bar"]["dependencies"]
    assert "baz" in content["group"]["bar"]["dependencies"]

    expected = """\

[tool.poetry.group.bar.dependencies]
baz = "^1.0.0"

"""
    string_content = content.as_string()
    if "\r\n" in string_content:
        # consistent line endings
        expected = expected.replace("\n", "\r\n")

    assert expected in string_content


def test_remove_command_should_not_write_changes_upon_installer_errors(
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    command_tester_factory: CommandTesterFactory,
    mocker: MockerFixture,
):
    repo.add_package(Package("foo", "2.0.0"))

    command_tester_factory("add").execute("foo")

    mocker.patch("poetry.installation.installer.Installer.run", return_value=1)

    original_content = app.poetry.file.read().as_string()

    tester.execute("foo")

    assert app.poetry.file.read().as_string() == original_content


def test_remove_with_dry_run_keep_files_intact(
    poetry_with_up_to_date_lockfile: Poetry,
    repo: TestRepository,
    command_tester_factory: CommandTesterFactory,
):
    tester = command_tester_factory("remove", poetry=poetry_with_up_to_date_lockfile)

    original_pyproject_content = poetry_with_up_to_date_lockfile.file.read()
    original_lockfile_content = poetry_with_up_to_date_lockfile._locker.lock_data

    repo.add_package(get_package("docker", "4.3.1"))

    tester.execute("docker --dry-run")

    assert poetry_with_up_to_date_lockfile.file.read() == original_pyproject_content
    assert (
        poetry_with_up_to_date_lockfile._locker.lock_data == original_lockfile_content
    )
