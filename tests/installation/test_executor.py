# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

import pytest

from clikit.api.formatter.style import Style
from clikit.io.buffered_io import BufferedIO

from poetry.config.config import Config
from poetry.core.packages.package import Package
from poetry.installation.executor import Executor
from poetry.installation.operations import Install
from poetry.installation.operations import Uninstall
from poetry.installation.operations import Update
from poetry.repositories.pool import Pool
from poetry.utils._compat import PY36
from poetry.utils._compat import Path
from poetry.utils.env import MockEnv
from tests.repositories.test_pypi_repository import MockRepository


@pytest.fixture()
def io():
    io = BufferedIO()
    io.formatter.add_style(Style("c1_dark").fg("cyan").dark())
    io.formatter.add_style(Style("c2_dark").fg("default").bold().dark())
    io.formatter.add_style(Style("success_dark").fg("green").dark())
    io.formatter.add_style(Style("warning").fg("yellow"))

    return io


@pytest.fixture()
def pool():
    pool = Pool()
    pool.add_repository(MockRepository())

    return pool


@pytest.fixture()
def mock_file_downloads(http):
    def callback(request, uri, headers):
        fixture = Path(__file__).parent.parent.joinpath(
            "fixtures/distributions/demo-0.1.0-py2.py3-none-any.whl"
        )

        with fixture.open("rb") as f:
            return [200, headers, f.read()]

    http.register_uri(
        http.GET,
        re.compile("^https://files.pythonhosted.org/.*$"),
        body=callback,
    )


def test_execute_executes_a_batch_of_operations(
    config, pool, io, tmp_dir, mock_file_downloads
):
    config = Config()
    config.merge({"cache-dir": tmp_dir})

    env = MockEnv(path=Path(tmp_dir))
    executor = Executor(env, pool, config, io)

    file_package = Package("demo", "0.1.0")
    file_package.source_type = "file"
    file_package.source_url = str(
        Path(__file__)
        .parent.parent.joinpath(
            "fixtures/distributions/demo-0.1.0-py2.py3-none-any.whl"
        )
        .resolve()
    )

    directory_package = Package("simple-project", "1.2.3")
    directory_package.source_type = "directory"
    directory_package.source_url = str(
        Path(__file__).parent.parent.joinpath("fixtures/simple_project").resolve()
    )

    git_package = Package("demo", "0.1.0")
    git_package.source_type = "git"
    git_package.source_reference = "master"
    git_package.source_url = "https://github.com/demo/demo.git"

    assert 0 == executor.execute(
        [
            Install(Package("pytest", "3.5.2")),
            Uninstall(Package("attrs", "17.4.0")),
            Update(Package("requests", "2.18.3"), Package("requests", "2.18.4")),
            Uninstall(Package("clikit", "0.2.3")).skip("Not currently installed"),
            Install(file_package),
            Install(directory_package),
            Install(git_package),
        ]
    )

    expected = """
Package operations: 4 installs, 1 update, 1 removal

  • Installing pytest (3.5.2)
  • Removing attrs (17.4.0)
  • Updating requests (2.18.3 -> 2.18.4)
  • Installing demo (0.1.0 {})
  • Installing simple-project (1.2.3 {})
  • Installing demo (0.1.0 master)
""".format(
        file_package.source_url, directory_package.source_url
    )
    assert expected == io.fetch_output()
    assert 5 == len(env.executed)


def test_execute_shows_skipped_operations_if_verbose(config, pool, io):
    config = Config()
    config.merge({"cache-dir": "/foo"})

    env = MockEnv()
    executor = Executor(env, pool, config, io)
    executor.verbose()

    assert 0 == executor.execute(
        [Uninstall(Package("clikit", "0.2.3")).skip("Not currently installed")]
    )

    expected = """
Package operations: 0 installs, 0 updates, 0 removals, 1 skipped

  • Removing clikit (0.2.3): Skipped for the following reason: Not currently installed
"""
    assert expected == io.fetch_output()
    assert 0 == len(env.executed)


@pytest.mark.skipif(
    not PY36, reason="Improved error rendering is only available on Python >=3.6"
)
def test_execute_should_show_errors(config, mocker, io):
    env = MockEnv()
    executor = Executor(env, pool, config, io)
    executor.verbose()

    mocker.patch.object(executor, "_install", side_effect=Exception("It failed!"))

    assert 1 == executor.execute([Install(Package("clikit", "0.2.3"))])

    expected = """
Package operations: 1 install, 0 updates, 0 removals

  • Installing clikit (0.2.3)

  Exception

  It failed!
"""

    assert expected in io.fetch_output()


def test_execute_should_show_operation_as_cancelled_on_subprocess_keyboard_interrupt(
    config, mocker, io
):
    env = MockEnv()
    executor = Executor(env, pool, config, io)
    executor.verbose()

    # A return code of -2 means KeyboardInterrupt in the pip subprocess
    mocker.patch.object(executor, "_install", return_value=-2)

    assert 1 == executor.execute([Install(Package("clikit", "0.2.3"))])

    expected = """
Package operations: 1 install, 0 updates, 0 removals

  • Installing clikit (0.2.3)
  • Installing clikit (0.2.3): Cancelled
"""

    assert expected == io.fetch_output()
