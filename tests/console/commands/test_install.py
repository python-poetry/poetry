from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.core.masonry.utils.module import ModuleOrPackageNotFound
from poetry.core.packages.dependency_group import MAIN_GROUP


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
fizz = { version = "^1.0", optional = true }
buzz = { version = "^2.0", optional = true }

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

[tool.poetry.extras]
extras_a = [ "fizz" ]
extras_b = [ "buzz" ]
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
        ("", {MAIN_GROUP, "foo", "bar", "baz", "bim"}),
        ("--only-root", set()),
        (f"--only {MAIN_GROUP}", {MAIN_GROUP}),
        ("--only foo", {"foo"}),
        ("--only foo,bar", {"foo", "bar"}),
        ("--only bam", {"bam"}),
        ("--with bam", {MAIN_GROUP, "foo", "bar", "baz", "bim", "bam"}),
        ("--without foo,bar", {MAIN_GROUP, "baz", "bim"}),
        (f"--without {MAIN_GROUP}", {"foo", "bar", "baz", "bim"}),
        ("--with foo,bar --without baz --without bim --only bam", {"bam"}),
        # net result zero options
        ("--with foo", {MAIN_GROUP, "foo", "bar", "baz", "bim"}),
        ("--without bam", {MAIN_GROUP, "foo", "bar", "baz", "bim"}),
        ("--with bam --without bam", {MAIN_GROUP, "foo", "bar", "baz", "bim"}),
        ("--with foo --without foo", {MAIN_GROUP, "bar", "baz", "bim"}),
        # deprecated options
        ("--no-dev", {MAIN_GROUP}),
    ],
)
@pytest.mark.parametrize("with_root", [True, False])
def test_group_options_are_passed_to_the_installer(
    options: str,
    groups: set[str],
    with_root: bool,
    tester: CommandTester,
    mocker: MockerFixture,
):
    """
    Group options are passed properly to the installer.
    """
    mocker.patch.object(tester.command.installer, "run", return_value=0)
    editable_builder_mock = mocker.patch(
        "poetry.masonry.builders.editable.EditableBuilder",
        side_effect=ModuleOrPackageNotFound(),
    )

    if not with_root:
        options = f"--no-root {options}"

    status_code = tester.execute(options)

    if options == "--no-root --only-root":
        assert status_code == 1
        return
    else:
        assert status_code == 0

    package_groups = set(tester.command.poetry.package._dependency_groups.keys())
    installer_groups = set(tester.command.installer._groups)

    assert installer_groups <= package_groups
    assert set(installer_groups) == groups

    if with_root:
        assert editable_builder_mock.call_count == 1
        assert editable_builder_mock.call_args_list[0][0][0] == tester.command.poetry
    else:
        assert editable_builder_mock.call_count == 0


def test_sync_option_is_passed_to_the_installer(
    tester: CommandTester, mocker: MockerFixture
):
    """
    The --sync option is passed properly to the installer.
    """
    mocker.patch.object(tester.command.installer, "run", return_value=1)

    tester.execute("--sync")

    assert tester.command.installer._requires_synchronization


def test_no_all_extras_doesnt_populate_installer(
    tester: CommandTester, mocker: MockerFixture
):
    """
    Not passing --all-extras means the installer doesn't see any extras.
    """
    mocker.patch.object(tester.command.installer, "run", return_value=1)

    tester.execute()

    assert not tester.command.installer._extras


def test_all_extras_populates_installer(tester: CommandTester, mocker: MockerFixture):
    """
    The --all-extras option results in extras passed to the installer.
    """
    mocker.patch.object(tester.command.installer, "run", return_value=1)

    tester.execute("--all-extras")

    assert tester.command.installer._extras == ["extras-a", "extras-b"]


def test_extras_are_parsed_and_populate_installer(
    tester: CommandTester,
    mocker: MockerFixture,
):
    mocker.patch.object(tester.command.installer, "run", return_value=0)

    tester.execute('--extras "first second third"')

    assert tester.command.installer._extras == ["first", "second", "third"]


def test_extras_conflicts_all_extras(tester: CommandTester, mocker: MockerFixture):
    """
    The --extras doesn't make sense with --all-extras.
    """
    mocker.patch.object(tester.command.installer, "run", return_value=0)

    tester.execute("--extras foo --all-extras")

    assert tester.status_code == 1
    assert (
        tester.io.fetch_error()
        == "You cannot specify explicit `--extras` while installing using"
        " `--all-extras`.\n"
    )


@pytest.mark.parametrize(
    "options",
    [
        "--with foo",
        "--without foo",
        "--with foo,bar --without baz",
        "--only foo",
    ],
)
def test_only_root_conflicts_with_without_only(
    options: str,
    tester: CommandTester,
    mocker: MockerFixture,
):
    mocker.patch.object(tester.command.installer, "run", return_value=0)

    tester.execute(f"{options} --only-root")

    assert tester.status_code == 1
    assert (
        tester.io.fetch_error()
        == "The `--with`, `--without` and `--only` options cannot be used with"
        " the `--only-root` option.\n"
    )


def test_remove_untracked_outputs_deprecation_warning(
    tester: CommandTester,
    mocker: MockerFixture,
):
    mocker.patch.object(tester.command.installer, "run", return_value=0)

    tester.execute("--remove-untracked")

    assert tester.status_code == 0
    assert (
        tester.io.fetch_error()
        == "The `--remove-untracked` option is deprecated, use the `--sync` option"
        " instead.\n"
    )


def test_dry_run_populates_installer(tester: CommandTester, mocker: MockerFixture):
    """
    The --dry-run option results in extras passed to the installer.
    """

    mocker.patch.object(tester.command.installer, "run", return_value=1)

    tester.execute("--dry-run")

    assert tester.command.installer._dry_run is True


def test_dry_run_does_not_build(tester: CommandTester, mocker: MockerFixture):
    mocker.patch.object(tester.command.installer, "run", return_value=0)
    mocked_editable_builder = mocker.patch(
        "poetry.masonry.builders.editable.EditableBuilder"
    )

    tester.execute("--dry-run")

    assert mocked_editable_builder.return_value.build.call_count == 0


def test_install_logs_output(tester: CommandTester, mocker: MockerFixture):
    mocker.patch.object(tester.command.installer, "run", return_value=0)
    mocker.patch("poetry.masonry.builders.editable.EditableBuilder")

    tester.execute()

    assert tester.status_code == 0
    assert (
        tester.io.fetch_output()
        == "\nInstalling the current project: simple-project (1.2.3)\n"
    )


def test_install_logs_output_decorated(tester: CommandTester, mocker: MockerFixture):
    mocker.patch.object(tester.command.installer, "run", return_value=0)
    mocker.patch("poetry.masonry.builders.editable.EditableBuilder")

    tester.execute(decorated=True)

    expected = (
        "\n"
        "\x1b[39;1mInstalling\x1b[39;22m the current project: "
        "\x1b[36msimple-project\x1b[39m (\x1b[39;1m1.2.3\x1b[39;22m)"
        "\x1b[1G\x1b[2K"
        "\x1b[39;1mInstalling\x1b[39;22m the current project: "
        "\x1b[36msimple-project\x1b[39m (\x1b[32m1.2.3\x1b[39m)"
        "\n"
    )
    assert tester.status_code == 0
    assert tester.io.fetch_output() == expected
