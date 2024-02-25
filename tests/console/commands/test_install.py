from __future__ import annotations

import re

from typing import TYPE_CHECKING

import pytest

from poetry.core.masonry.utils.module import ModuleOrPackageNotFound
from poetry.core.packages.dependency_group import MAIN_GROUP

from poetry.console.commands.installer_command import InstallerCommand
from poetry.console.exceptions import GroupNotFound
from tests.helpers import TestLocker


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry
    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter
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


def _project_factory(
    fixture_name: str,
    project_factory: ProjectFactory,
    fixture_dir: FixtureDirGetter,
) -> Poetry:
    source = fixture_dir(fixture_name)
    pyproject_content = (source / "pyproject.toml").read_text(encoding="utf-8")
    poetry_lock_content = (source / "poetry.lock").read_text(encoding="utf-8")
    return project_factory(
        name="foobar",
        pyproject_content=pyproject_content,
        poetry_lock_content=poetry_lock_content,
        source=source,
    )


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
) -> None:
    """
    Group options are passed properly to the installer.
    """
    assert isinstance(tester.command, InstallerCommand)
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

    package_groups = set(tester.command.poetry.package._dependency_groups)
    installer_groups = set(tester.command.installer._groups or [])

    assert installer_groups <= package_groups
    assert set(installer_groups) == groups

    if with_root:
        assert editable_builder_mock.call_count == 1
        assert editable_builder_mock.call_args_list[0][0][0] == tester.command.poetry
    else:
        assert editable_builder_mock.call_count == 0


def test_sync_option_is_passed_to_the_installer(
    tester: CommandTester, mocker: MockerFixture
) -> None:
    """
    The --sync option is passed properly to the installer.
    """
    assert isinstance(tester.command, InstallerCommand)
    mocker.patch.object(tester.command.installer, "run", return_value=1)

    tester.execute("--sync")

    assert tester.command.installer._requires_synchronization


@pytest.mark.parametrize("compile", [False, True])
def test_compile_option_is_passed_to_the_installer(
    tester: CommandTester, mocker: MockerFixture, compile: bool
) -> None:
    """
    The --compile option is passed properly to the installer.
    """
    assert isinstance(tester.command, InstallerCommand)
    mocker.patch.object(tester.command.installer, "run", return_value=1)
    enable_bytecode_compilation_mock = mocker.patch.object(
        tester.command.installer.executor._wheel_installer,
        "enable_bytecode_compilation",
    )

    tester.execute("--compile" if compile else "")

    enable_bytecode_compilation_mock.assert_called_once_with(compile)


@pytest.mark.parametrize("skip_directory_cli_value", [True, False])
def test_no_directory_is_passed_to_installer(
    tester: CommandTester, mocker: MockerFixture, skip_directory_cli_value: bool
) -> None:
    """
    The --no-directory option is passed to the installer.
    """

    assert isinstance(tester.command, InstallerCommand)
    mocker.patch.object(tester.command.installer, "run", return_value=1)

    if skip_directory_cli_value is True:
        tester.execute("--no-directory")
    else:
        tester.execute()

    assert tester.command.installer._skip_directory is skip_directory_cli_value


def test_no_all_extras_doesnt_populate_installer(
    tester: CommandTester, mocker: MockerFixture
) -> None:
    """
    Not passing --all-extras means the installer doesn't see any extras.
    """
    assert isinstance(tester.command, InstallerCommand)
    mocker.patch.object(tester.command.installer, "run", return_value=1)

    tester.execute()

    assert not tester.command.installer._extras


def test_all_extras_populates_installer(
    tester: CommandTester, mocker: MockerFixture
) -> None:
    """
    The --all-extras option results in extras passed to the installer.
    """
    assert isinstance(tester.command, InstallerCommand)
    mocker.patch.object(tester.command.installer, "run", return_value=1)

    tester.execute("--all-extras")

    assert tester.command.installer._extras == ["extras-a", "extras-b"]


def test_extras_are_parsed_and_populate_installer(
    tester: CommandTester,
    mocker: MockerFixture,
) -> None:
    assert isinstance(tester.command, InstallerCommand)
    mocker.patch.object(tester.command.installer, "run", return_value=0)

    tester.execute('--extras "first second third"')

    assert tester.command.installer._extras == ["first", "second", "third"]


def test_extras_conflicts_all_extras(
    tester: CommandTester, mocker: MockerFixture
) -> None:
    """
    The --extras doesn't make sense with --all-extras.
    """
    assert isinstance(tester.command, InstallerCommand)
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
) -> None:
    assert isinstance(tester.command, InstallerCommand)
    mocker.patch.object(tester.command.installer, "run", return_value=0)

    tester.execute(f"{options} --only-root")

    assert tester.status_code == 1
    assert (
        tester.io.fetch_error()
        == "The `--with`, `--without` and `--only` options cannot be used with"
        " the `--only-root` option.\n"
    )


@pytest.mark.parametrize(
    ("options", "valid_groups", "should_raise"),
    [
        ({"--with": MAIN_GROUP}, {MAIN_GROUP}, False),
        ({"--with": "spam"}, set(), True),
        ({"--with": "spam,foo"}, {"foo"}, True),
        ({"--without": "spam"}, set(), True),
        ({"--without": "spam,bar"}, {"bar"}, True),
        ({"--with": "eggs,ham", "--without": "spam"}, set(), True),
        ({"--with": "eggs,ham", "--without": "spam,baz"}, {"baz"}, True),
        ({"--only": "spam"}, set(), True),
        ({"--only": "bim"}, {"bim"}, False),
        ({"--only": MAIN_GROUP}, {MAIN_GROUP}, False),
    ],
)
def test_invalid_groups_with_without_only(
    tester: CommandTester,
    mocker: MockerFixture,
    options: dict[str, str],
    valid_groups: set[str],
    should_raise: bool,
) -> None:
    assert isinstance(tester.command, InstallerCommand)
    mocker.patch.object(tester.command.installer, "run", return_value=0)

    cmd_args = " ".join(f"{flag} {groups}" for (flag, groups) in options.items())

    if not should_raise:
        tester.execute(cmd_args)
        assert tester.status_code == 0
    else:
        with pytest.raises(GroupNotFound, match=r"^Group\(s\) not found:") as e:
            tester.execute(cmd_args)
        assert tester.status_code is None
        for opt, groups in options.items():
            group_list = groups.split(",")
            invalid_groups = sorted(set(group_list) - valid_groups)
            for group in invalid_groups:
                assert (
                    re.search(rf"{group} \(via .*{opt}.*\)", str(e.value)) is not None
                )


def test_remove_untracked_outputs_deprecation_warning(
    tester: CommandTester,
    mocker: MockerFixture,
) -> None:
    assert isinstance(tester.command, InstallerCommand)
    mocker.patch.object(tester.command.installer, "run", return_value=0)

    tester.execute("--remove-untracked")

    assert tester.status_code == 0
    assert (
        "The `--remove-untracked` option is deprecated, use the `--sync` option"
        " instead.\n" in tester.io.fetch_error()
    )


def test_dry_run_populates_installer(
    tester: CommandTester, mocker: MockerFixture
) -> None:
    """
    The --dry-run option results in extras passed to the installer.
    """

    assert isinstance(tester.command, InstallerCommand)
    mocker.patch.object(tester.command.installer, "run", return_value=1)

    tester.execute("--dry-run")

    assert tester.command.installer._dry_run is True


def test_dry_run_does_not_build(tester: CommandTester, mocker: MockerFixture) -> None:
    assert isinstance(tester.command, InstallerCommand)
    mocker.patch.object(tester.command.installer, "run", return_value=0)
    mocked_editable_builder = mocker.patch(
        "poetry.masonry.builders.editable.EditableBuilder"
    )

    tester.execute("--dry-run")

    assert mocked_editable_builder.return_value.build.call_count == 0


def test_install_logs_output(tester: CommandTester, mocker: MockerFixture) -> None:
    assert isinstance(tester.command, InstallerCommand)
    mocker.patch.object(tester.command.installer, "run", return_value=0)
    mocker.patch("poetry.masonry.builders.editable.EditableBuilder")

    tester.execute()

    assert tester.status_code == 0
    assert (
        tester.io.fetch_output()
        == "\nInstalling the current project: simple-project (1.2.3)\n"
    )


def test_install_logs_output_decorated(
    tester: CommandTester, mocker: MockerFixture
) -> None:
    assert isinstance(tester.command, InstallerCommand)
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


@pytest.mark.parametrize("with_root", [True, False])
@pytest.mark.parametrize("error", ["module", "readme", ""])
def test_install_warning_corrupt_root(
    command_tester_factory: CommandTesterFactory,
    project_factory: ProjectFactory,
    with_root: bool,
    error: str,
) -> None:
    name = "corrupt"
    content = f"""\
[tool.poetry]
name = "{name}"
version = "1.2.3"
description = ""
authors = []
"""
    if error == "readme":
        content += 'readme = "missing_readme.md"\n'
    poetry = project_factory(name=name, pyproject_content=content)
    if error != "module":
        (poetry.pyproject_path.parent / f"{name}.py").touch()

    tester = command_tester_factory("install", poetry=poetry)
    tester.execute("" if with_root else "--no-root")

    assert tester.status_code == 0
    if with_root and error:
        assert "The current project could not be installed: " in tester.io.fetch_error()
    else:
        assert tester.io.fetch_error() == ""


@pytest.mark.parametrize("options", ["", "--without dev"])
@pytest.mark.parametrize(
    "project", ["missing_directory_dependency", "missing_file_dependency"]
)
def test_install_path_dependency_does_not_exist(
    command_tester_factory: CommandTesterFactory,
    project_factory: ProjectFactory,
    fixture_dir: FixtureDirGetter,
    project: str,
    options: str,
) -> None:
    poetry = _project_factory(project, project_factory, fixture_dir)
    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.locked(True)
    tester = command_tester_factory("install", poetry=poetry)
    if options:
        tester.execute(options)
    else:
        with pytest.raises(ValueError, match="does not exist"):
            tester.execute(options)


@pytest.mark.parametrize("options", ["", "--extras notinstallable"])
def test_install_extra_path_dependency_does_not_exist(
    command_tester_factory: CommandTesterFactory,
    project_factory: ProjectFactory,
    fixture_dir: FixtureDirGetter,
    options: str,
) -> None:
    project = "missing_extra_directory_dependency"
    poetry = _project_factory(project, project_factory, fixture_dir)
    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.locked(True)
    tester = command_tester_factory("install", poetry=poetry)
    if not options:
        tester.execute(options)
    else:
        with pytest.raises(ValueError, match="does not exist"):
            tester.execute(options)


@pytest.mark.parametrize("options", ["", "--no-directory"])
def test_install_missing_directory_dependency_with_no_directory(
    command_tester_factory: CommandTesterFactory,
    project_factory: ProjectFactory,
    fixture_dir: FixtureDirGetter,
    options: str,
) -> None:
    poetry = _project_factory(
        "missing_directory_dependency", project_factory, fixture_dir
    )
    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.locked(True)
    tester = command_tester_factory("install", poetry=poetry)
    if options:
        tester.execute(options)
    else:
        with pytest.raises(ValueError, match="does not exist"):
            tester.execute(options)


def test_non_package_mode_does_not_try_to_install_root(
    command_tester_factory: CommandTesterFactory,
    project_factory: ProjectFactory,
) -> None:
    content = """\
[tool.poetry]
package-mode = false
"""
    poetry = project_factory(name="non-package-mode", pyproject_content=content)

    tester = command_tester_factory("install", poetry=poetry)
    tester.execute()

    assert tester.status_code == 0
    assert tester.io.fetch_error() == ""
