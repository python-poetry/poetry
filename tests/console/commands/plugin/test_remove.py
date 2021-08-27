<<<<<<< HEAD
from typing import TYPE_CHECKING

import pytest
import tomlkit

from poetry.core.packages.package import Package

from poetry.__version__ import __version__
from poetry.layouts.layout import POETRY_DEFAULT


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from poetry.console.commands.remove import RemoveCommand
    from poetry.repositories import Repository
    from poetry.utils.env import MockEnv
    from tests.helpers import PoetryTestApplication
    from tests.types import CommandTesterFactory


@pytest.fixture()
def tester(command_tester_factory: "CommandTesterFactory") -> "CommandTester":
=======
import pytest
import tomlkit

from poetry.__version__ import __version__
from poetry.core.packages.package import Package
from poetry.layouts.layout import POETRY_DEFAULT


@pytest.fixture()
def tester(command_tester_factory):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return command_tester_factory("plugin remove")


@pytest.fixture()
<<<<<<< HEAD
def pyproject(env: "MockEnv") -> None:
=======
def pyproject(env):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    pyproject = tomlkit.loads(POETRY_DEFAULT)
    content = pyproject["tool"]["poetry"]

    content["name"] = "poetry"
    content["version"] = __version__
    content["description"] = ""
    content["authors"] = ["Sébastien Eustace <sebastien@eustace.io>"]

    dependency_section = content["dependencies"]
    dependency_section["python"] = "^3.6"

    env.path.joinpath("pyproject.toml").write_text(
        tomlkit.dumps(pyproject), encoding="utf-8"
    )


@pytest.fixture(autouse=True)
<<<<<<< HEAD
def install_plugin(env: "MockEnv", installed: "Repository", pyproject: None) -> None:
=======
def install_plugin(env, installed, pyproject):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    lock_content = {
        "package": [
            {
                "name": "poetry-plugin",
                "version": "1.2.3",
                "category": "main",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
        ],
        "metadata": {
            "python-versions": "^3.6",
            "platform": "*",
            "content-hash": "123456789",
            "hashes": {"poetry-plugin": []},
        },
    }

    env.path.joinpath("poetry.lock").write_text(
        tomlkit.dumps(lock_content), encoding="utf-8"
    )

<<<<<<< HEAD
    pyproject_toml = tomlkit.loads(
        env.path.joinpath("pyproject.toml").read_text(encoding="utf-8")
    )
    content = pyproject_toml["tool"]["poetry"]
=======
    pyproject = tomlkit.loads(
        env.path.joinpath("pyproject.toml").read_text(encoding="utf-8")
    )
    content = pyproject["tool"]["poetry"]
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

    dependency_section = content["dependencies"]
    dependency_section["poetry-plugin"] = "^1.2.3"

    env.path.joinpath("pyproject.toml").write_text(
<<<<<<< HEAD
        tomlkit.dumps(pyproject_toml), encoding="utf-8"
=======
        tomlkit.dumps(pyproject), encoding="utf-8"
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    )

    installed.add_package(Package("poetry-plugin", "1.2.3"))


<<<<<<< HEAD
def test_remove_installed_package(
    app: "PoetryTestApplication", tester: "CommandTester", env: "MockEnv"
):
=======
def test_remove_installed_package(app, tester, env):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    tester.execute("poetry-plugin")

    expected = """\
Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 0 installs, 0 updates, 1 removal

  • Removing poetry-plugin (1.2.3)
"""

    assert tester.io.fetch_output() == expected

<<<<<<< HEAD
    remove_command: "RemoveCommand" = app.find("remove")
=======
    remove_command = app.find("remove")
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    assert remove_command.poetry.file.parent == env.path
    assert remove_command.poetry.locker.lock.parent == env.path
    assert remove_command.poetry.locker.lock.exists()
    assert not remove_command.installer.executor._dry_run

    content = remove_command.poetry.file.read()["tool"]["poetry"]
    assert "poetry-plugin" not in content["dependencies"]


<<<<<<< HEAD
def test_remove_installed_package_dry_run(
    app: "PoetryTestApplication", tester: "CommandTester", env: "MockEnv"
):
=======
def test_remove_installed_package_dry_run(app, tester, env):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    tester.execute("poetry-plugin --dry-run")

    expected = """\
Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 0 installs, 0 updates, 1 removal

  • Removing poetry-plugin (1.2.3)
  • Removing poetry-plugin (1.2.3)
"""

    assert tester.io.fetch_output() == expected

<<<<<<< HEAD
    remove_command: "RemoveCommand" = app.find("remove")
=======
    remove_command = app.find("remove")
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    assert remove_command.poetry.file.parent == env.path
    assert remove_command.poetry.locker.lock.parent == env.path
    assert remove_command.poetry.locker.lock.exists()
    assert remove_command.installer.executor._dry_run

    content = remove_command.poetry.file.read()["tool"]["poetry"]
    assert "poetry-plugin" in content["dependencies"]
