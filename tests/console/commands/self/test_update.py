from pathlib import Path

import pytest

from poetry.__version__ import __version__
from poetry.console.exceptions import PoetrySimpleConsoleException
from poetry.core.packages.package import Package
from poetry.core.semver.version import Version
from poetry.factory import Factory
from poetry.repositories.installed_repository import InstalledRepository
from poetry.repositories.pool import Pool
from poetry.repositories.repository import Repository
from poetry.utils.env import EnvManager


FIXTURES = Path(__file__).parent.joinpath("fixtures")


@pytest.fixture()
def tester(command_tester_factory):
    return command_tester_factory("self update")


def test_self_update_can_update_from_recommended_installation(
    tester, http, mocker, environ, tmp_venv
):
    mocker.patch.object(EnvManager, "get_system_env", return_value=tmp_venv)

    command = tester.command
    command._data_dir = tmp_venv.path.parent

    new_version = Version.parse(__version__).next_minor().text

    old_poetry = Package("poetry", __version__)
    old_poetry.add_dependency(Factory.create_dependency("cleo", "^0.8.2"))

    new_poetry = Package("poetry", new_version)
    new_poetry.add_dependency(Factory.create_dependency("cleo", "^1.0.0"))

    installed_repository = Repository()
    installed_repository.add_package(old_poetry)
    installed_repository.add_package(Package("cleo", "0.8.2"))

    repository = Repository()
    repository.add_package(new_poetry)
    repository.add_package(Package("cleo", "1.0.0"))

    pool = Pool()
    pool.add_repository(repository)

    command._pool = pool

    mocker.patch.object(InstalledRepository, "load", return_value=installed_repository)

    tester.execute()

    expected_output = """\
Updating Poetry to 1.2.0

Updating dependencies
Resolving dependencies...

Package operations: 0 installs, 2 updates, 0 removals

  - Updating cleo (0.8.2 -> 1.0.0)
  - Updating poetry ({} -> {})

Updating the poetry script

Poetry ({}) is installed now. Great!
""".format(
        __version__, new_version, new_version
    )

    assert tester.io.fetch_output() == expected_output


def test_self_update_does_not_update_non_recommended_installation(
    tester, http, mocker, environ, tmp_venv
):
    mocker.patch.object(EnvManager, "get_system_env", return_value=tmp_venv)

    command = tester.command

    new_version = Version.parse(__version__).next_minor().text

    old_poetry = Package("poetry", __version__)
    old_poetry.add_dependency(Factory.create_dependency("cleo", "^0.8.2"))

    new_poetry = Package("poetry", new_version)
    new_poetry.add_dependency(Factory.create_dependency("cleo", "^1.0.0"))

    installed_repository = Repository()
    installed_repository.add_package(old_poetry)
    installed_repository.add_package(Package("cleo", "0.8.2"))

    repository = Repository()
    repository.add_package(new_poetry)
    repository.add_package(Package("cleo", "1.0.0"))

    pool = Pool()
    pool.add_repository(repository)

    command._pool = pool

    with pytest.raises(PoetrySimpleConsoleException):
        tester.execute()
