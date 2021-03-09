import pytest
import tomlkit

from poetry.__version__ import __version__
from poetry.core.packages.package import Package
from poetry.factory import Factory
from poetry.layouts.layout import POETRY_DEFAULT
from poetry.repositories.installed_repository import InstalledRepository
from poetry.repositories.pool import Pool
from poetry.utils.env import EnvManager


@pytest.fixture()
def tester(command_tester_factory):
    return command_tester_factory("plugin remove")


@pytest.fixture()
def installed():
    repository = InstalledRepository()

    repository.add_package(Package("poetry", __version__))

    return repository


def configure_sources_factory(repo):
    def _configure_sources(poetry, sources, config, io):
        pool = Pool()
        pool.add_repository(repo)
        poetry.set_pool(pool)

    return _configure_sources


@pytest.fixture(autouse=True)
def setup_mocks(mocker, env, repo, installed):
    mocker.patch.object(EnvManager, "get_system_env", return_value=env)
    mocker.patch.object(InstalledRepository, "load", return_value=installed)
    mocker.patch.object(
        Factory, "configure_sources", side_effect=configure_sources_factory(repo)
    )


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


def test_remove_installed_package(app, repo, tester, env, installed, pyproject):
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


def test_remove_installed_package_dry_run(app, repo, tester, env, installed, pyproject):
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
