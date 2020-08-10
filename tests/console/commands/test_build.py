import re

import pytest

from tests.helpers import get_package


@pytest.fixture
def command_tester_with_build_requires(
    repo, make_poetry, make_installer_command_tester
):
    repo.add_package(get_package("cython", "0.29.6"))
    poetry = make_poetry("project_with_build_system_requires")
    return make_installer_command_tester(poetry, "build")


@pytest.fixture
def command_tester(project_directory, make_poetry, make_installer_command_tester):
    return make_installer_command_tester(make_poetry(project_directory), "build")


def test_build_project_complete(command_tester):
    tester = command_tester
    command_tester.execute()

    assert tester._command.installer.executor.installations_count == 0

    output = tester.io.fetch_output()

    assert "Writing lock file" not in output
    assert "Building sdist" in output
    assert "Built simple-project-1.2.3.tar.gz" in output
    assert "Building wheel" in output
    assert re.search(r"Built simple_project-1\.2\.3-.*\.whl", output) is not None


def test_build_project_sdist(command_tester):
    tester = command_tester
    command_tester.execute("-f sdist")

    assert tester._command.installer.executor.installations_count == 0

    output = tester.io.fetch_output()

    assert "Writing lock file" not in output
    assert "Building sdist" in output
    assert "Built simple-project-1.2.3.tar.gz" in output
    assert "Building wheel" not in output
    assert re.search(r"Built simple_project-1\.2\.3-.*\.whl", output) is None


def test_build_project_wheel(command_tester):
    tester = command_tester
    command_tester.execute("-f wheel")

    assert tester._command.installer.executor.installations_count == 0

    output = tester.io.fetch_output()

    assert "Writing lock file" not in output
    assert "Building sdist" not in output
    assert "Built simple-project-1.2.3.tar.gz" not in output
    assert "Building wheel" in output
    assert re.search(r"Built simple_project-1\.2\.3-.*\.whl", output) is not None


def test_build_project_with_build_requires(command_tester_with_build_requires):
    tester = command_tester_with_build_requires
    tester.execute()

    assert tester._command.installer.executor.installations_count == 1

    package = tester._command.installer.executor._installs[0]
    assert package.name == "cython"
    assert package.version.text == "0.29.6"

    output = tester.io.fetch_output()

    assert "Writing lock file" in output
    assert "Building sdist" in output
    assert "Built project-1.2.3.tar.gz" in output
    assert "Building wheel" in output
    assert re.search(r"Built project-1\.2\.3-.*\.whl", output) is not None
