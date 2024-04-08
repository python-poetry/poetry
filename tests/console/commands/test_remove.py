from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import cast

import pytest
import tomlkit

from poetry.core.packages.package import Package

from poetry.factory import Factory
from tests.helpers import TestLocker
from tests.helpers import get_package


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture
    from tomlkit import TOMLDocument

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

    poetry = project_factory(
        name="foobar",
        pyproject_content=(source / "pyproject.toml").read_text(encoding="utf-8"),
        poetry_lock_content=(source / "poetry.lock").read_text(encoding="utf-8"),
    )

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.locked(True)
    return poetry


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("remove")


def test_remove_without_specific_group_removes_from_all_groups(
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    installed: Repository,
) -> None:
    """
    Removing without specifying a group removes packages from all groups.
    """
    installed.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("baz", "1.0.0"))

    pyproject: dict[str, Any] = app.poetry.file.read()

    groups_content: dict[str, Any] = tomlkit.parse(
        """\
[tool.poetry.group.bar.dependencies]
foo = "^2.0.0"
baz = "^1.0.0"

"""
    )
    pyproject["tool"]["poetry"]["dependencies"]["foo"] = "^2.0.0"
    pyproject["tool"]["poetry"]["group"] = groups_content["tool"]["poetry"]["group"]
    pyproject = cast("TOMLDocument", pyproject)
    app.poetry.file.write(pyproject)

    app.poetry.package.add_dependency(Factory.create_dependency("foo", "^2.0.0"))
    app.poetry.package.add_dependency(
        Factory.create_dependency("foo", "^2.0.0", groups=["bar"])
    )
    app.poetry.package.add_dependency(
        Factory.create_dependency("baz", "^1.0.0", groups=["bar"])
    )

    tester.execute("foo")

    pyproject = app.poetry.file.read()
    pyproject = cast("dict[str, Any]", pyproject)
    content = pyproject["tool"]["poetry"]
    assert "foo" not in content["dependencies"]
    assert "foo" not in content["group"]["bar"]["dependencies"]
    assert "baz" in content["group"]["bar"]["dependencies"]

    expected = """\

[tool.poetry.group.bar.dependencies]
baz = "^1.0.0"

"""
    pyproject = cast("TOMLDocument", pyproject)
    string_content = pyproject.as_string()
    if "\r\n" in string_content:
        # consistent line endings
        expected = expected.replace("\n", "\r\n")

    assert expected in string_content


def test_remove_without_specific_group_removes_from_specific_groups(
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    installed: Repository,
) -> None:
    """
    Removing with a specific group given removes packages only from this group.
    """
    installed.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("baz", "1.0.0"))

    pyproject: dict[str, Any] = app.poetry.file.read()

    groups_content: dict[str, Any] = tomlkit.parse(
        """\
[tool.poetry.group.bar.dependencies]
foo = "^2.0.0"
baz = "^1.0.0"

"""
    )
    pyproject["tool"]["poetry"]["dependencies"]["foo"] = "^2.0.0"
    pyproject["tool"]["poetry"]["group"] = groups_content["tool"]["poetry"]["group"]
    pyproject = cast("TOMLDocument", pyproject)
    app.poetry.file.write(pyproject)

    app.poetry.package.add_dependency(Factory.create_dependency("foo", "^2.0.0"))
    app.poetry.package.add_dependency(
        Factory.create_dependency("foo", "^2.0.0", groups=["bar"])
    )
    app.poetry.package.add_dependency(
        Factory.create_dependency("baz", "^1.0.0", groups=["bar"])
    )

    tester.execute("foo --group bar")

    pyproject = app.poetry.file.read()
    pyproject = cast("dict[str, Any]", pyproject)
    content = pyproject["tool"]["poetry"]
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
    installed: Repository,
) -> None:
    """
    Empty groups are automatically discarded after package removal.
    """
    installed.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("baz", "1.0.0"))

    content: dict[str, Any] = app.poetry.file.read()

    groups_content: dict[str, Any] = tomlkit.parse(
        """\
[tool.poetry.group.bar.dependencies]
foo = "^2.0.0"
baz = "^1.0.0"

"""
    )
    content["tool"]["poetry"]["dependencies"]["foo"] = "^2.0.0"
    content["tool"]["poetry"]["group"] = groups_content["tool"]["poetry"]["group"]
    content = cast("TOMLDocument", content)
    app.poetry.file.write(content)

    app.poetry.package.add_dependency(Factory.create_dependency("foo", "^2.0.0"))
    app.poetry.package.add_dependency(
        Factory.create_dependency("foo", "^2.0.0", groups=["bar"])
    )
    app.poetry.package.add_dependency(
        Factory.create_dependency("baz", "^1.0.0", groups=["bar"])
    )

    tester.execute("foo baz --group bar")

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]
    assert "foo" in content["dependencies"]
    assert "foo" not in content["group"]["bar"]["dependencies"]
    assert "baz" not in content["group"]["bar"]["dependencies"]
    content = cast("TOMLDocument", content)
    assert "[tool.poetry.group.bar]" not in content.as_string()
    assert "[tool.poetry.group]" not in content.as_string()


def test_remove_canonicalized_named_removes_dependency_correctly(
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    installed: Repository,
) -> None:
    """
    Removing a dependency using a canonicalized named removes the dependency.
    """
    installed.add_package(Package("foo-bar", "2.0.0"))
    repo.add_package(Package("foo-bar", "2.0.0"))
    repo.add_package(Package("baz", "1.0.0"))

    pyproject: dict[str, Any] = app.poetry.file.read()

    groups_content: dict[str, Any] = tomlkit.parse(
        """\
[tool.poetry.group.bar.dependencies]
foo-bar = "^2.0.0"
baz = "^1.0.0"

"""
    )
    pyproject["tool"]["poetry"]["dependencies"]["foo-bar"] = "^2.0.0"
    pyproject["tool"]["poetry"].value._insert_after(
        "dependencies", "group", groups_content["tool"]["poetry"]["group"]
    )
    pyproject = cast("TOMLDocument", pyproject)
    app.poetry.file.write(pyproject)

    app.poetry.package.add_dependency(Factory.create_dependency("foo-bar", "^2.0.0"))
    app.poetry.package.add_dependency(
        Factory.create_dependency("foo-bar", "^2.0.0", groups=["bar"])
    )
    app.poetry.package.add_dependency(
        Factory.create_dependency("baz", "^1.0.0", groups=["bar"])
    )

    tester.execute("Foo_Bar")

    pyproject = app.poetry.file.read()
    pyproject = cast("dict[str, Any]", pyproject)
    content = pyproject["tool"]["poetry"]
    assert "foo-bar" not in content["dependencies"]
    assert "foo-bar" not in content["group"]["bar"]["dependencies"]
    assert "baz" in content["group"]["bar"]["dependencies"]

    expected = """\

[tool.poetry.group.bar.dependencies]
baz = "^1.0.0"

"""
    pyproject = cast("TOMLDocument", pyproject)
    string_content = pyproject.as_string()
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
) -> None:
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
) -> None:
    tester = command_tester_factory("remove", poetry=poetry_with_up_to_date_lockfile)

    original_pyproject_content = poetry_with_up_to_date_lockfile.file.read()
    original_lockfile_content = poetry_with_up_to_date_lockfile._locker.lock_data

    repo.add_package(get_package("docker", "4.3.1"))

    tester.execute("docker --dry-run")

    assert poetry_with_up_to_date_lockfile.file.read() == original_pyproject_content
    assert (
        poetry_with_up_to_date_lockfile._locker.lock_data == original_lockfile_content
    )


def test_remove_performs_uninstall_op(
    poetry_with_up_to_date_lockfile: Poetry,
    command_tester_factory: CommandTesterFactory,
    installed: Repository,
) -> None:
    installed.add_package(get_package("docker", "4.3.1"))
    tester = command_tester_factory("remove", poetry=poetry_with_up_to_date_lockfile)

    tester.execute("docker")

    expected = """\
Updating dependencies
Resolving dependencies...

Package operations: 0 installs, 0 updates, 1 removal

  - Removing docker (4.3.1)

Writing lock file
"""

    assert tester.io.fetch_output() == expected


def test_remove_with_lock_does_not_perform_uninstall_op(
    poetry_with_up_to_date_lockfile: Poetry,
    command_tester_factory: CommandTesterFactory,
    installed: Repository,
) -> None:
    installed.add_package(get_package("docker", "4.3.1"))
    tester = command_tester_factory("remove", poetry=poetry_with_up_to_date_lockfile)

    tester.execute("docker --lock")

    expected = """\
Updating dependencies
Resolving dependencies...

Writing lock file
"""

    assert tester.io.fetch_output() == expected
