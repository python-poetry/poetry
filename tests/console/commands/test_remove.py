import pytest

from poetry.core.packages.package import Package


@pytest.fixture()
def tester(command_tester_factory):
    return command_tester_factory("remove")


def test_remove_command_should_not_write_changes_upon_installer_errors(
    tester, app, repo, command_tester_factory, mocker
):
    repo.add_package(Package("foo", "2.0.0"))

    command_tester_factory("add").execute("foo")

    mocker.patch("poetry.installation.installer.Installer.run", return_value=1)

    original_content = app.poetry.file.read().as_string()

    tester.execute("foo")

    assert app.poetry.file.read().as_string() == original_content
