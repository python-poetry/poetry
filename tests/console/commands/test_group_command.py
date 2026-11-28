from __future__ import annotations

import re

from typing import TYPE_CHECKING

import pytest

from poetry.core.packages.dependency_group import MAIN_GROUP

from poetry.console.commands.group_command import GroupCommand
from poetry.console.commands.installer_command import InstallerCommand
from poetry.console.commands.show import ShowCommand
from poetry.console.exceptions import GroupNotFoundError
from tests.helpers import DummyLocker


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry
    from tests.types import CommandTesterFactory
    from tests.types import ProjectFactory


PYPROJECT_CONTENT = """\
[tool.poetry]
name = "simple-project"
version = "1.2.3"
description = "Some description."
authors = [
    "Python Poetry <tests@python-poetry.org>"
]
license = "MIT"

[tool.poetry.dependencies]
python = "^3.11"

[tool.poetry.group.foo.dependencies]
foo = "^1.0"

[tool.poetry.group.bar.dependencies]
bar = "^1.1"

[tool.poetry.group.baz.dependencies]
baz = "^1.2"

[tool.poetry.group.Dev_Tools]
optional = true

[tool.poetry.group.Dev_Tools.dependencies]
black = "^24.0"

[tool.poetry.group.qux]
optional = true

[tool.poetry.group.qux.dependencies]
qux = "^1.3"
"""


LOCK_DATA = {
    "package": [
        {
            "name": "foo",
            "version": "1.0.0",
            "description": "Foo package",
            "optional": False,
            "platform": "*",
            "python-versions": "*",
            "checksum": [],
        },
        {
            "name": "bar",
            "version": "1.1.0",
            "description": "Bar package",
            "optional": False,
            "platform": "*",
            "python-versions": "*",
            "checksum": [],
        },
        {
            "name": "baz",
            "version": "1.2.0",
            "description": "Baz package",
            "optional": False,
            "platform": "*",
            "python-versions": "*",
            "checksum": [],
        },
        {
            "name": "black",
            "version": "24.0.0",
            "description": "Black package",
            "optional": True,
            "platform": "*",
            "python-versions": "*",
            "checksum": [],
        },
        {
            "name": "qux",
            "version": "1.3.0",
            "description": "Qux package",
            "optional": True,
            "platform": "*",
            "python-versions": "*",
            "checksum": [],
        },
    ],
    "metadata": {
        "python-versions": "*",
        "platform": "*",
        "content-hash": "123456789",
        "files": {"foo": [], "bar": [], "baz": [], "black": [], "qux": []},
    },
}

NON_OPTIONAL_GROUPS = {MAIN_GROUP, "foo", "bar", "baz"}
ALL_GROUPS = NON_OPTIONAL_GROUPS | {"dev-tools", "qux"}


@pytest.fixture
def command() -> str:
    return "install"


@pytest.fixture
def poetry(project_factory: ProjectFactory) -> Poetry:
    return project_factory(name="simple-project", pyproject_content=PYPROJECT_CONTENT)


@pytest.fixture
def tester(
    command_tester_factory: CommandTesterFactory, command: str, poetry: Poetry
) -> CommandTester:
    return command_tester_factory(command)


@pytest.fixture
def show_tester(
    command_tester_factory: CommandTesterFactory, poetry: Poetry
) -> CommandTester:
    return command_tester_factory("show")


def test_group_dependency_options() -> None:
    """
    The group dependency options shared by all group commands accept multiple
    comma-separated values.
    """
    options = GroupCommand._group_dependency_options()

    assert [option.name for option in options] == ["without", "with", "only"]

    for option in options:
        assert option.is_flag() is False
        assert option.is_list() is True


def test_default_group_is_none(tester: CommandTester) -> None:
    assert isinstance(tester.command, InstallerCommand)

    assert tester.command.default_group is None


def test_default_groups_are_the_non_optional_groups(tester: CommandTester) -> None:
    assert isinstance(tester.command, InstallerCommand)

    assert tester.command.default_groups == tester.command.non_optional_groups
    assert tester.command.non_optional_groups == NON_OPTIONAL_GROUPS


def test_activated_groups_default_to_the_non_optional_groups(
    tester: CommandTester, mocker: MockerFixture
) -> None:
    assert isinstance(tester.command, InstallerCommand)
    mocker.patch.object(tester.command.installer, "run", return_value=0)

    tester.execute("")

    assert tester.command.activated_groups == NON_OPTIONAL_GROUPS


def test_only_takes_precedence_over_with_and_without(
    tester: CommandTester, mocker: MockerFixture
) -> None:
    assert isinstance(tester.command, InstallerCommand)
    mocker.patch.object(tester.command.installer, "run", return_value=0)

    tester.execute("--only foo --with qux --without bar")

    assert tester.command.activated_groups == {"foo"}
    assert "are ignored when used along with" in tester.io.fetch_error()


def test_all_groups_includes_optional_groups(
    tester: CommandTester, mocker: MockerFixture
) -> None:
    assert isinstance(tester.command, InstallerCommand)
    mocker.patch.object(tester.command.installer, "run", return_value=0)

    tester.execute("--all-groups")

    assert tester.command.activated_groups == ALL_GROUPS


@pytest.mark.parametrize(
    ("options", "expected_groups"),
    [
        ("--with qux", NON_OPTIONAL_GROUPS | {"qux"}),
        ("--without foo,bar", {MAIN_GROUP, "baz"}),
        ("--with qux --with Dev_Tools", ALL_GROUPS),
        ('--with "qux , Dev_Tools"', ALL_GROUPS),
    ],
)
def test_group_names_are_normalized(
    options: str,
    expected_groups: set[str],
    tester: CommandTester,
    mocker: MockerFixture,
) -> None:
    """
    Group names given on the command line are canonicalized, so that e.g.
    Dev_Tools refers to the group declared as Dev_Tools in pyproject.toml,
    and values may be combined across occurrences and split on commas.
    """
    assert isinstance(tester.command, InstallerCommand)
    mocker.patch.object(tester.command.installer, "run", return_value=0)

    tester.execute(options)

    assert tester.command.activated_groups == expected_groups


def test_unknown_group_error_keeps_the_original_spelling(
    tester: CommandTester, mocker: MockerFixture
) -> None:
    assert isinstance(tester.command, InstallerCommand)
    mocker.patch.object(tester.command.installer, "run", return_value=0)

    with pytest.raises(GroupNotFoundError, match=r"^Group\(s\) not found:") as e:
        tester.execute("--with No_Such")

    assert re.search(r"No_Such \(via .*--with.*\)", str(e.value))


def test_project_with_activated_groups_only(
    tester: CommandTester, mocker: MockerFixture
) -> None:
    assert isinstance(tester.command, InstallerCommand)
    mocker.patch.object(tester.command.installer, "run", return_value=0)

    tester.execute("--only foo,bar")

    project = tester.command.project_with_activated_groups_only()

    assert set(project.dependency_group_names(include_optional=True)) == {"foo", "bar"}


def test_group_options_on_a_command_without_all_groups(
    show_tester: CommandTester, poetry: Poetry
) -> None:
    """
    The group options are shared with commands that do not define the
    all-groups option themselves.
    """
    assert isinstance(show_tester.command, ShowCommand)
    assert isinstance(poetry.locker, DummyLocker)
    poetry.locker.mock_lock_data(LOCK_DATA)

    show_tester.execute("--with qux")

    assert show_tester.status_code == 0
    assert show_tester.command.activated_groups == NON_OPTIONAL_GROUPS | {"qux"}
    project = show_tester.command.project_with_activated_groups_only()
    assert set(project.dependency_group_names(include_optional=True)) == (
        NON_OPTIONAL_GROUPS | {"qux"}
    )
