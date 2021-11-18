from pathlib import Path
from typing import TYPE_CHECKING
from typing import Type

import pytest

from poetry.core.packages.package import Package
from poetry.core.semver.version import Version

from poetry.__version__ import __version__
from poetry.console.exceptions import PoetrySimpleConsoleException
from poetry.factory import Factory
from poetry.repositories.installed_repository import InstalledRepository
from poetry.repositories.pool import Pool
from poetry.repositories.repository import Repository
from poetry.utils.env import EnvManager


if TYPE_CHECKING:
    import httpretty

    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.utils.env import VirtualEnv
    from tests.types import CommandTesterFactory

FIXTURES = Path(__file__).parent.joinpath("fixtures")


@pytest.fixture()
def tester(command_tester_factory: "CommandTesterFactory") -> "CommandTester":
    return command_tester_factory("self update")


def test_self_update_can_update_from_recommended_installation(
    tester: "CommandTester",
    http: Type["httpretty.httpretty"],
    mocker: "MockerFixture",
    environ: None,
    tmp_venv: "VirtualEnv",
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

    expected_output = f"""\
Updating Poetry to 1.2.0

Updating dependencies
Resolving dependencies...

Package operations: 0 installs, 2 updates, 0 removals

  - Updating cleo (0.8.2 -> 1.0.0)
  - Updating poetry ({__version__} -> {new_version})

Updating the poetry script

Poetry ({new_version}) is installed now. Great!
"""

    assert tester.io.fetch_output() == expected_output


def test_self_update_does_not_update_non_recommended_installation(
    tester: "CommandTester",
    http: Type["httpretty.httpretty"],
    mocker: "MockerFixture",
    environ: None,
    tmp_venv: "VirtualEnv",
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
