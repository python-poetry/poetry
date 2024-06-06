from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.factory import Factory
from poetry.packages import Locker
from poetry.toml import TOMLFile


if TYPE_CHECKING:
    from collections.abc import Iterator

    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry
    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter
    from tests.types import SetProjectContext


@pytest.fixture
def poetry_simple_project(set_project_context: SetProjectContext) -> Iterator[Poetry]:
    with set_project_context("simple_project", in_place=False) as cwd:
        yield Factory().create_poetry(cwd)


@pytest.fixture
def poetry_with_outdated_lockfile(
    set_project_context: SetProjectContext,
) -> Iterator[Poetry]:
    with set_project_context("outdated_lock", in_place=False) as cwd:
        yield Factory().create_poetry(cwd)


@pytest.fixture
def poetry_with_up_to_date_lockfile(
    set_project_context: SetProjectContext,
) -> Iterator[Poetry]:
    with set_project_context("up_to_date_lock", in_place=False) as cwd:
        yield Factory().create_poetry(cwd)


@pytest.fixture
def poetry_with_pypi_reference(
    set_project_context: SetProjectContext,
) -> Iterator[Poetry]:
    with set_project_context("pypi_reference", in_place=False) as cwd:
        yield Factory().create_poetry(cwd)


@pytest.fixture
def poetry_with_invalid_pyproject(
    set_project_context: SetProjectContext,
) -> Iterator[Poetry]:
    with set_project_context("invalid_pyproject", in_place=False) as cwd:
        yield Factory().create_poetry(cwd)


@pytest.fixture()
def tester(
    command_tester_factory: CommandTesterFactory, poetry_simple_project: Poetry
) -> CommandTester:
    return command_tester_factory("check", poetry=poetry_simple_project)


def test_check_valid(tester: CommandTester) -> None:
    tester.execute()

    expected = """\
All set!
"""

    assert tester.io.fetch_output() == expected


def test_check_valid_legacy(
    mocker: MockerFixture, tester: CommandTester, fixture_dir: FixtureDirGetter
) -> None:
    mocker.patch(
        "poetry.poetry.Poetry.file",
        return_value=TOMLFile(fixture_dir("simple_project_legacy") / "pyproject.toml"),
        new_callable=mocker.PropertyMock,
    )
    tester.execute()

    expected = (
        "Warning: [tool.poetry.name] is deprecated. Use [project.name] instead.\n"
        "Warning: [tool.poetry.version] is set but 'version' is not in "
        "[project.dynamic]. If it is static use [project.version]. If it is dynamic, "
        "add 'version' to [project.dynamic].\n"
        "If you want to set the version dynamically via `poetry build "
        "--local-version` or you are using a plugin, which sets the version "
        "dynamically, you should define the version in [tool.poetry] and add "
        "'version' to [project.dynamic].\n"
        "Warning: [tool.poetry.description] is deprecated. Use [project.description] "
        "instead.\n"
        "Warning: [tool.poetry.readme] is set but 'readme' is not in "
        "[project.dynamic]. If it is static use [project.readme]. If it is dynamic, "
        "add 'readme' to [project.dynamic].\n"
        "If you want to define multiple readmes, you should define them in "
        "[tool.poetry] and add 'readme' to [project.dynamic].\n"
        "Warning: [tool.poetry.license] is deprecated. Use [project.license] instead.\n"
        "Warning: [tool.poetry.authors] is deprecated. Use [project.authors] instead.\n"
        "Warning: [tool.poetry.keywords] is deprecated. Use [project.keywords] "
        "instead.\n"
        "Warning: [tool.poetry.classifiers] is set but 'classifiers' is not in "
        "[project.dynamic]. If it is static use [project.classifiers]. If it is "
        "dynamic, add 'classifiers' to [project.dynamic].\n"
        "ATTENTION: Per default Poetry determines classifiers for supported Python "
        "versions and license automatically. If you define classifiers in [project], "
        "you disable the automatic enrichment. In other words, you have to define all "
        "classifiers manually. If you want to use Poetry's automatic enrichment of "
        "classifiers, you should define them in [tool.poetry] and add 'classifiers' "
        "to [project.dynamic].\n"
        "Warning: [tool.poetry.homepage] is deprecated. Use [project.urls] instead.\n"
        "Warning: [tool.poetry.repository] is deprecated. Use [project.urls] instead.\n"
        "Warning: [tool.poetry.documentation] is deprecated. Use [project.urls] "
        "instead.\n"
        "Warning: Defining console scripts in [tool.poetry.scripts] is deprecated. "
        "Use [project.scripts] instead. ([tool.poetry.scripts] should only be used "
        "for scripts of type 'file').\n"
    )

    assert tester.io.fetch_error() == expected


def test_check_invalid_dep_name_same_as_project_name(
    mocker: MockerFixture, tester: CommandTester, fixture_dir: FixtureDirGetter
) -> None:
    mocker.patch(
        "poetry.poetry.Poetry.file",
        return_value=TOMLFile(
            fixture_dir("invalid_pyproject_dep_name") / "pyproject.toml"
        ),
        new_callable=mocker.PropertyMock,
    )
    tester.execute("--lock")
    fastjsonschema_error = "data must contain ['description'] properties"
    custom_error = "The fields ['description'] are required in package mode."
    expected_template = """\
Error: Project name (invalid) is same as one of its dependencies
Error: Unrecognized classifiers: ['Intended Audience :: Clowns'].
Error: Declared README file does not exist: never/exists.md
Error: Invalid source "exists" referenced in dependencies.
Error: Invalid source "not-exists" referenced in dependencies.
Error: Invalid source "not-exists2" referenced in dependencies.
Error: poetry.lock was not found.
Warning: A wildcard Python dependency is ambiguous.\
 Consider specifying a more explicit one.
Warning: The "pendulum" dependency specifies the "allows-prereleases" property,\
 which is deprecated. Use "allow-prereleases" instead.
Warning: Deprecated classifier 'Natural Language :: Ukranian'.\
 Must be replaced by ['Natural Language :: Ukrainian'].
Warning: Deprecated classifier\
 'Topic :: Communications :: Chat :: AOL Instant Messenger'.\
 Must be removed.
"""
    expected = {
        expected_template.format(schema_error=schema_error)
        for schema_error in (fastjsonschema_error, custom_error)
    }

    assert tester.io.fetch_error() in expected


def test_check_invalid(
    tester: CommandTester,
    fixture_dir: FixtureDirGetter,
    command_tester_factory: CommandTesterFactory,
    poetry_with_invalid_pyproject: Poetry,
) -> None:
    tester = command_tester_factory("check", poetry=poetry_with_invalid_pyproject)
    tester.execute("--lock")

    expected = """\
Error: Unrecognized classifiers: ['Intended Audience :: Clowns'].
Error: Declared README file does not exist: never/exists.md
Error: Invalid source "not-exists" referenced in dependencies.
Error: Invalid source "not-exists2" referenced in dependencies.
Error: poetry.lock was not found.
Warning: A wildcard Python dependency is ambiguous.\
 Consider specifying a more explicit one.
Warning: The "pendulum" dependency specifies the "allows-prereleases" property,\
 which is deprecated. Use "allow-prereleases" instead.
Warning: Deprecated classifier 'Natural Language :: Ukranian'.\
 Must be replaced by ['Natural Language :: Ukrainian'].
Warning: Deprecated classifier\
 'Topic :: Communications :: Chat :: AOL Instant Messenger'.\
 Must be removed.
"""

    assert tester.io.fetch_error() == expected


def test_check_private(
    mocker: MockerFixture, tester: CommandTester, fixture_dir: FixtureDirGetter
) -> None:
    mocker.patch(
        "poetry.poetry.Poetry.file",
        return_value=TOMLFile(fixture_dir("private_pyproject") / "pyproject.toml"),
        new_callable=mocker.PropertyMock,
    )

    tester.execute()

    expected = """\
All set!
"""

    assert tester.io.fetch_output() == expected


def test_check_non_package_mode(
    mocker: MockerFixture, tester: CommandTester, fixture_dir: FixtureDirGetter
) -> None:
    mocker.patch(
        "poetry.poetry.Poetry.file",
        return_value=TOMLFile(fixture_dir("non_package_mode") / "pyproject.toml"),
        new_callable=mocker.PropertyMock,
    )

    tester.execute()

    expected = """\
All set!
"""

    assert tester.io.fetch_output() == expected


@pytest.mark.parametrize(
    ("options", "expected", "expected_status"),
    [
        ("", "All set!\n", 0),
        ("--lock", "Error: poetry.lock was not found.\n", 1),
    ],
)
def test_check_lock_missing(
    mocker: MockerFixture,
    tester: CommandTester,
    fixture_dir: FixtureDirGetter,
    options: str,
    expected: str,
    expected_status: int,
) -> None:
    mocker.patch(
        "poetry.poetry.Poetry.file",
        return_value=TOMLFile(fixture_dir("private_pyproject") / "pyproject.toml"),
        new_callable=mocker.PropertyMock,
    )

    status_code = tester.execute(options)

    assert status_code == expected_status

    if status_code == 0:
        assert tester.io.fetch_output() == expected
    else:
        assert tester.io.fetch_error() == expected


@pytest.mark.parametrize("options", ["", "--lock"])
def test_check_lock_outdated(
    command_tester_factory: CommandTesterFactory,
    poetry_with_outdated_lockfile: Poetry,
    options: str,
) -> None:
    locker = Locker(
        lock=poetry_with_outdated_lockfile.pyproject.file.path.parent / "poetry.lock",
        pyproject_data=poetry_with_outdated_lockfile.locker._pyproject_data,
    )
    poetry_with_outdated_lockfile.set_locker(locker)

    tester = command_tester_factory("check", poetry=poetry_with_outdated_lockfile)
    status_code = tester.execute(options)
    expected = (
        "Error: pyproject.toml changed significantly since poetry.lock was last generated. "
        "Run `poetry lock [--no-update]` to fix the lock file.\n"
    )

    assert tester.io.fetch_error() == expected

    # exit with an error
    assert status_code == 1


@pytest.mark.parametrize("options", ["", "--lock"])
def test_check_lock_up_to_date(
    command_tester_factory: CommandTesterFactory,
    poetry_with_up_to_date_lockfile: Poetry,
    options: str,
) -> None:
    locker = Locker(
        lock=poetry_with_up_to_date_lockfile.pyproject.file.path.parent / "poetry.lock",
        pyproject_data=poetry_with_up_to_date_lockfile.locker._pyproject_data,
    )
    poetry_with_up_to_date_lockfile.set_locker(locker)

    tester = command_tester_factory("check", poetry=poetry_with_up_to_date_lockfile)
    status_code = tester.execute(options)
    expected = "All set!\n"
    assert tester.io.fetch_output() == expected

    # exit with an error
    assert status_code == 0


def test_check_does_not_error_on_pypi_reference(
    command_tester_factory: CommandTesterFactory,
    poetry_with_pypi_reference: Poetry,
) -> None:
    tester = command_tester_factory("check", poetry=poetry_with_pypi_reference)
    status_code = tester.execute("")

    assert tester.io.fetch_output() == "All set!\n"
    assert status_code == 0
