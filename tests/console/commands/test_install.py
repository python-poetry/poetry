from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


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
readme = "README.rst"

[tool.poetry.dependencies]
python = "~2.7 || ^3.4"

[tool.poetry.group.foo.dependencies]
foo = "^1.0"

[tool.poetry.group.bar.dependencies]
bar = "^1.1"

[tool.poetry.group.baz.dependencies]
baz = "^1.2"

[tool.poetry.group.bim.dependencies]
bim = "^1.3"

[tool.poetry.group.bam]
optional = true

[tool.poetry.group.bam.dependencies]
bam = "^1.4"
"""


@pytest.fixture
def poetry(project_factory: ProjectFactory) -> Poetry:
    return project_factory(name="export", pyproject_content=PYPROJECT_CONTENT)


@pytest.fixture
def tester(
    command_tester_factory: CommandTesterFactory, poetry: Poetry
) -> CommandTester:
    return command_tester_factory("install")


@pytest.mark.parametrize(
    ("options", "groups"),
    [
        ("", {"default", "foo", "bar", "baz", "bim"}),
        ("--only default", {"default"}),
        ("--only foo", {"foo"}),
        ("--only foo,bar", {"foo", "bar"}),
        ("--only bam", {"bam"}),
        ("--with bam", {"default", "foo", "bar", "baz", "bim", "bam"}),
        ("--without foo,bar", {"default", "baz", "bim"}),
        ("--with foo,bar --without baz --without bim --only bam", {"bam"}),
    ],
)
def test_group_options_are_passed_to_the_installer(
    options: str, groups: set[str], tester: CommandTester, mocker: MockerFixture
):
    """
    Group options are passed properly to the installer.
    """
    mocker.patch.object(tester.command.installer, "run", return_value=1)

    tester.execute(options)

    package_groups = set(tester.command.poetry.package._dependency_groups.keys())
    installer_groups = set(tester.command.installer._groups)

    assert installer_groups <= package_groups
    assert set(installer_groups) == groups


def test_sync_option_is_passed_to_the_installer(
    tester: CommandTester, mocker: MockerFixture
):
    """
    The --sync option is passed properly to the installer.
    """
    mocker.patch.object(tester.command.installer, "run", return_value=1)

    tester.execute("--sync")

    assert tester.command.installer._requires_synchronization
