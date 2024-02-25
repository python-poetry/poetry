from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.packages import Locker
from poetry.toml import TOMLFile


if TYPE_CHECKING:
    import httpretty

    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry
    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter
    from tests.types import ProjectFactory


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("check")


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


@pytest.fixture
def poetry_with_outdated_lockfile(
    project_factory: ProjectFactory, fixture_dir: FixtureDirGetter
) -> Poetry:
    return _project_factory("outdated_lock", project_factory, fixture_dir)


@pytest.fixture
def poetry_with_up_to_date_lockfile(
    project_factory: ProjectFactory, fixture_dir: FixtureDirGetter
) -> Poetry:
    return _project_factory("up_to_date_lock", project_factory, fixture_dir)


def test_check_valid(tester: CommandTester) -> None:
    tester.execute()

    expected = """\
All set!
"""

    assert tester.io.fetch_output() == expected


def test_check_invalid(
    mocker: MockerFixture, tester: CommandTester, fixture_dir: FixtureDirGetter
) -> None:
    mocker.patch(
        "poetry.poetry.Poetry.file",
        return_value=TOMLFile(fixture_dir("invalid_pyproject") / "pyproject.toml"),
        new_callable=mocker.PropertyMock,
    )

    tester.execute("--lock")

    fastjsonschema_error = "data must contain ['description'] properties"
    custom_error = "The fields ['description'] are required in package mode."
    expected_template = """\
Error: {schema_error}
Error: Project name (invalid) is same as one of its dependencies
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
    expected = {
        expected_template.format(schema_error=schema_error)
        for schema_error in (fastjsonschema_error, custom_error)
    }

    assert tester.io.fetch_error() in expected


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
    http: type[httpretty.httpretty],
    options: str,
) -> None:
    http.disable()

    locker = Locker(
        lock=poetry_with_outdated_lockfile.pyproject.file.path.parent / "poetry.lock",
        local_config=poetry_with_outdated_lockfile.locker._local_config,
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
    http: type[httpretty.httpretty],
    options: str,
) -> None:
    http.disable()

    locker = Locker(
        lock=poetry_with_up_to_date_lockfile.pyproject.file.path.parent / "poetry.lock",
        local_config=poetry_with_up_to_date_lockfile.locker._local_config,
    )
    poetry_with_up_to_date_lockfile.set_locker(locker)

    tester = command_tester_factory("check", poetry=poetry_with_up_to_date_lockfile)
    status_code = tester.execute(options)
    expected = "All set!\n"
    assert tester.io.fetch_output() == expected

    # exit with an error
    assert status_code == 0
