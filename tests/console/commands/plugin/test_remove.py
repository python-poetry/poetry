import pytest
import tomlkit

from poetry.__version__ import __version__
from poetry.core.packages.package import Package
from poetry.layouts.layout import POETRY_DEFAULT


@pytest.fixture()
def tester(command_tester_factory):
    return command_tester_factory("plugin remove")


@pytest.fixture()
def pyproject(env):
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
def install_plugin(env, installed, pyproject):
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

    pyproject = tomlkit.loads(
        env.path.joinpath("pyproject.toml").read_text(encoding="utf-8")
    )
    content = pyproject["tool"]["poetry"]

    dependency_section = content["dependencies"]
    dependency_section["poetry-plugin"] = "^1.2.3"

    env.path.joinpath("pyproject.toml").write_text(
        tomlkit.dumps(pyproject), encoding="utf-8"
    )

    installed.add_package(Package("poetry-plugin", "1.2.3"))


def test_remove_installed_package(app, tester, env):
    tester.execute("poetry-plugin")

    expected = """\
Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 0 installs, 0 updates, 1 removal

  • Removing poetry-plugin (1.2.3)
"""

    assert tester.io.fetch_output() == expected

    remove_command = app.find("remove")
    assert remove_command.poetry.file.parent == env.path
    assert remove_command.poetry.locker.lock.parent == env.path
    assert remove_command.poetry.locker.lock.exists()
    assert not remove_command.installer.executor._dry_run

    content = remove_command.poetry.file.read()["tool"]["poetry"]
    assert "poetry-plugin" not in content["dependencies"]


def test_remove_installed_package_dry_run(app, tester, env):
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

    remove_command = app.find("remove")
    assert remove_command.poetry.file.parent == env.path
    assert remove_command.poetry.locker.lock.parent == env.path
    assert remove_command.poetry.locker.lock.exists()
    assert remove_command.installer.executor._dry_run

    content = remove_command.poetry.file.read()["tool"]["poetry"]
    assert "poetry-plugin" in content["dependencies"]
