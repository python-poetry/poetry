import os

import pytest

from poetry.__version__ import __version__
from poetry.core.packages.package import Package
from poetry.core.semver.version import Version
from poetry.factory import Factory
from poetry.repositories.installed_repository import InstalledRepository
from poetry.repositories.pool import Pool
from poetry.repositories.repository import Repository
from poetry.utils._compat import WINDOWS
from poetry.utils._compat import Path
from poetry.utils.env import EnvManager


FIXTURES = Path(__file__).parent.joinpath("fixtures")


@pytest.fixture()
def tester(command_tester_factory):
    return command_tester_factory("self update")


def test_self_update_should_install_all_necessary_elements(
    tester, http, mocker, environ, tmp_dir
):
    os.environ["POETRY_HOME"] = tmp_dir

    command = tester._command

    version = Version.parse(__version__).next_minor.text
    repository = Repository()
    repository.add_package(Package("poetry", version))

    pool = Pool()
    pool.add_repository(repository)

    command._pool = pool
    mocker.patch.object(command, "_check_recommended_installation", return_value=None)
    mocker.patch.object(
        command, "_get_release_name", return_value="poetry-{}-darwin".format(version)
    )
    mocker.patch("subprocess.check_output", return_value=b"Python 3.8.2")

    http.register_uri(
        "GET",
        command.BASE_URL + "/{}/poetry-{}-darwin.sha256sum".format(version, version),
        body=FIXTURES.joinpath("poetry-1.0.5-darwin.sha256sum").read_bytes(),
    )
    http.register_uri(
        "GET",
        command.BASE_URL + "/{}/poetry-{}-darwin.tar.gz".format(version, version),
        body=FIXTURES.joinpath("poetry-1.0.5-darwin.tar.gz").read_bytes(),
    )

    tester.execute()

    bin_ = Path(tmp_dir).joinpath("bin")
    lib = Path(tmp_dir).joinpath("lib")
    assert bin_.exists()

    script = bin_.joinpath("poetry")
    assert script.exists()

    expected_script = """\
# -*- coding: utf-8 -*-
import glob
import sys
import os

lib = os.path.normpath(os.path.join(os.path.realpath(__file__), "../..", "lib"))
vendors = os.path.join(lib, "poetry", "_vendor")
current_vendors = os.path.join(
    vendors, "py{}".format(".".join(str(v) for v in sys.version_info[:2]))
)
sys.path.insert(0, lib)
sys.path.insert(0, current_vendors)

if __name__ == "__main__":
    from poetry.console import main
    main()
"""
    if not WINDOWS:
        expected_script = "#!/usr/bin/env python\n" + expected_script

    assert expected_script == script.read_text()

    if WINDOWS:
        bat = bin_.joinpath("poetry.bat")
        expected_bat = '@echo off\r\npython "{}" %*\r\n'.format(
            str(script).replace(os.environ.get("USERPROFILE", ""), "%USERPROFILE%")
        )
        assert bat.exists()
        with bat.open(newline="") as f:
            assert expected_bat == f.read()

    assert lib.exists()
    assert lib.joinpath("poetry").exists()


def test_self_update_can_update_from_recommended_installation(
    tester, http, mocker, environ, tmp_venv
):
    mocker.patch.object(EnvManager, "get_system_env", return_value=tmp_venv)
    target_script = tmp_venv.path.parent.joinpath("venv/bin/poetry")
    if WINDOWS:
        target_script = tmp_venv.path.parent.joinpath("venv/Scripts/poetry.exe")

    target_script.parent.mkdir(parents=True, exist_ok=True)
    target_script.touch()

    command = tester._command
    command._data_dir = tmp_venv.path.parent

    new_version = Version.parse(__version__).next_minor.text

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
Updating Poetry to {}

Updating dependencies
Resolving dependencies...

Package operations: 0 installs, 2 updates, 0 removals

  - Updating cleo (0.8.2 -> 1.0.0)
  - Updating poetry ({} -> {})

Updating the poetry script

Poetry (1.2.0) is installed now. Great!
""".format(
        new_version, __version__, new_version
    )

    assert tester.io.fetch_output() == expected_output
