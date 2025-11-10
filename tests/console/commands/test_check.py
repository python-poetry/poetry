from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.factory import Factory
from poetry.packages import Locker
from poetry.toml import TOMLFile


if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

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


@pytest.mark.parametrize(
    ["args", "expected_status"],
    [
        ([], 0),
        (["--strict"], 1),
    ],
)
def test_check_valid_legacy(
    args: list[str],
    expected_status: int,
    mocker: MockerFixture,
    tester: CommandTester,
    fixture_dir: FixtureDirGetter,
) -> None:
    mocker.patch(
        "poetry.poetry.Poetry.file",
        return_value=TOMLFile(fixture_dir("simple_project_legacy") / "pyproject.toml"),
        new_callable=mocker.PropertyMock,
    )
    tester.execute(" ".join(args))

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
    assert tester.status_code == expected_status


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
    tester.execute("")

    expected = """\
Error: Project name (invalid) is same as one of its dependencies
"""

    assert tester.io.fetch_error() == expected


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
Warning: [project.license] is not a valid SPDX expression.\
 This is deprecated and will raise an error in the future.
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
        "Run `poetry lock` to fix the lock file.\n"
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


@pytest.fixture(params=["project_str", "project_dict", "poetry_str", "poetry_array"])
def pyproject_with_readme_file(tmp_path: Path, request: pytest.FixtureRequest) -> Path:
    pyproject_content = """\
[project]
name = "test"
version = "1.0.0"
"""
    if request.param == "project_str":
        pyproject_content += 'readme = "README.md"\n'

    elif request.param == "project_dict":
        pyproject_content += (
            'readme = { file = "README.md", content-type = "text/markdown" }\n'
        )
    elif request.param == "poetry_str":
        pyproject_content += """
[tool.poetry]
readme = "README.md"
"""
    elif request.param == "poetry_array":
        pyproject_content += """
[tool.poetry]
readme = ["README.md"]
"""
    else:
        raise ValueError(f"Unknown readme type: {request.param}")
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(pyproject_content, encoding="utf-8")
    return pyproject_path


@pytest.mark.parametrize("readme_exists", [True, False])
def test_check_readme_file_exists(
    mocker: MockerFixture,
    tester: CommandTester,
    fixture_dir: FixtureDirGetter,
    tmp_path: Path,
    pyproject_with_readme_file: Path,
    readme_exists: bool,
) -> None:
    if readme_exists:
        readme_path = tmp_path / "README.md"
        readme_path.write_text("README", encoding="utf-8")

    mocker.patch(
        "poetry.poetry.Poetry.file",
        return_value=TOMLFile(pyproject_with_readme_file),
        new_callable=mocker.PropertyMock,
    )
    result = tester.execute()

    if readme_exists:
        assert result == 0
        assert "Declared README file does not exist" not in tester.io.fetch_error()
    else:
        assert result == 1
        assert (
            "Declared README file does not exist: README.md" in tester.io.fetch_error()
        )


@pytest.fixture(params=["project_str", "project_dict", "poetry_str", "poetry_array"])
def pyproject_with_empty_readme_file(
    tmp_path: Path, request: pytest.FixtureRequest
) -> Path:
    pyproject_content = """\
[project]
name = "test"
version = "1.0.0"
"""
    if request.param == "project_str":
        pyproject_content += 'readme = ""\n'

    elif request.param == "project_dict":
        pyproject_content += 'readme = { file = "", content-type = "text/markdown" }\n'
    elif request.param == "poetry_str":
        pyproject_content += """
[tool.poetry]
readme = ""
"""
    elif request.param == "poetry_array":
        pyproject_content += """
[tool.poetry]
readme = [""]
"""
    else:
        raise ValueError(f"Unknown readme type: {request.param}")
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(pyproject_content, encoding="utf-8")
    return pyproject_path


def test_check_project_readme_as_text(
    mocker: MockerFixture,
    tester: CommandTester,
    fixture_dir: FixtureDirGetter,
    tmp_path: Path,
) -> None:
    pyproject_content = """[project]
name = "test"
version = "1.0.0"
readme = { content-type = "text/markdown", text = "README" }
"""
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(pyproject_content, encoding="utf-8")

    mocker.patch(
        "poetry.poetry.Poetry.file",
        return_value=TOMLFile(pyproject_path),
        new_callable=mocker.PropertyMock,
    )
    result = tester.execute()

    assert result == 0
    assert "Declared README file does not exist" not in tester.io.fetch_error()


def test_check_poetry_readme_multiple(
    mocker: MockerFixture,
    tester: CommandTester,
    fixture_dir: FixtureDirGetter,
    tmp_path: Path,
) -> None:
    pyproject_content = """[project]
name = "test"
version = "1.0.0"
dynamic = ["readme"]

[tool.poetry]
readme = ["README1.md", "README2.md", "README3.md", "README4.md"]
"""
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(pyproject_content, encoding="utf-8")
    (tmp_path / "README2.md").write_text("README 2", encoding="utf-8")
    (tmp_path / "README3.md").write_text("README 3", encoding="utf-8")

    mocker.patch(
        "poetry.poetry.Poetry.file",
        return_value=TOMLFile(pyproject_path),
        new_callable=mocker.PropertyMock,
    )
    result = tester.execute()

    assert result == 1
    assert tester.io.fetch_error() == (
        "Error: Declared README file does not exist: README1.md\n"
        "Error: Declared README file does not exist: README4.md\n"
    )
