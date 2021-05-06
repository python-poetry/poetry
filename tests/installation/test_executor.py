# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import re
import shutil

from pathlib import Path

import pytest

from cleo.formatters.style import Style
from cleo.io.buffered_io import BufferedIO

from poetry.config.config import Config
from poetry.core.packages.package import Package
from poetry.core.utils._compat import PY36
from poetry.installation.executor import Executor
from poetry.installation.operations import Install
from poetry.installation.operations import Uninstall
from poetry.installation.operations import Update
from poetry.repositories.pool import Pool
from poetry.utils.env import MockEnv
from tests.repositories.test_pypi_repository import MockRepository


@pytest.fixture
def env(tmp_dir):
    path = Path(tmp_dir) / ".venv"
    path.mkdir(parents=True)

    return MockEnv(path=path, is_venv=True)


@pytest.fixture()
def io():
    io = BufferedIO()
    io.output.formatter.set_style("c1_dark", Style("cyan", options=["dark"]))
    io.output.formatter.set_style("c2_dark", Style("default", options=["bold", "dark"]))
    io.output.formatter.set_style("success_dark", Style("green", options=["dark"]))
    io.output.formatter.set_style("warning", Style("yellow"))

    return io


@pytest.fixture()
def io_decorated():
    io = BufferedIO(decorated=True)
    io.output.formatter.set_style("c1", Style("cyan"))
    io.output.formatter.set_style("success", Style("green"))

    return io


@pytest.fixture()
def io_not_decorated():
    io = BufferedIO(decorated=False)

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
    mocker, config, pool, io, tmp_dir, mock_file_downloads, env
):
    pip_editable_install = mocker.patch(
        "poetry.installation.executor.pip_editable_install", unsafe=not PY36
    )

    config = Config()
    config.merge({"cache-dir": tmp_dir})

    executor = Executor(env, pool, config, io)

    file_package = Package(
        "demo",
        "0.1.0",
        source_type="file",
        source_url=Path(__file__)
        .parent.parent.joinpath(
            "fixtures/distributions/demo-0.1.0-py2.py3-none-any.whl"
        )
        .resolve()
        .as_posix(),
    )

    directory_package = Package(
        "simple-project",
        "1.2.3",
        source_type="directory",
        source_url=Path(__file__)
        .parent.parent.joinpath("fixtures/simple_project")
        .resolve()
        .as_posix(),
    )

    git_package = Package(
        "demo",
        "0.1.0",
        source_type="git",
        source_reference="master",
        source_url="https://github.com/demo/demo.git",
        develop=True,
    )

    return_code = executor.execute(
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

    expected = set(expected.splitlines())
    output = set(io.fetch_output().splitlines())
    assert expected == output
    assert 5 == len(env.executed)
    assert 0 == return_code
    pip_editable_install.assert_called_once()


def test_execute_shows_skipped_operations_if_verbose(
    config, pool, io, config_cache_dir, env
):
    config = Config()
    config.merge({"cache-dir": config_cache_dir.as_posix()})

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


def test_execute_should_show_errors(config, mocker, io, env):
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


def test_execute_works_with_ansi_output(
    mocker, config, pool, io_decorated, tmp_dir, mock_file_downloads, env
):
    config = Config()
    config.merge({"cache-dir": tmp_dir})

    executor = Executor(env, pool, config, io_decorated)

    install_output = (
        "some string that does not contain a keyb0ard !nterrupt or cance11ed by u$er"
    )
    mocker.patch.object(env, "_run", return_value=install_output)
    return_code = executor.execute(
        [
            Install(Package("pytest", "3.5.2")),
        ]
    )
    env._run.assert_called_once()

    expected = [
        "\x1b[39;1mPackage operations\x1b[39;22m: \x1b[34m1\x1b[39m install, \x1b[34m0\x1b[39m updates, \x1b[34m0\x1b[39m removals",
        "\x1b[34;1m•\x1b[39;22m \x1b[39mInstalling \x1b[39m\x1b[36mpytest\x1b[39m\x1b[39m (\x1b[39m\x1b[39;1m3.5.2\x1b[39;22m\x1b[39m)\x1b[39m: \x1b[34mPending...\x1b[39m",
        "\x1b[34;1m•\x1b[39;22m \x1b[39mInstalling \x1b[39m\x1b[36mpytest\x1b[39m\x1b[39m (\x1b[39m\x1b[39;1m3.5.2\x1b[39;22m\x1b[39m)\x1b[39m: \x1b[34mDownloading...\x1b[39m",
        "\x1b[34;1m•\x1b[39;22m \x1b[39mInstalling \x1b[39m\x1b[36mpytest\x1b[39m\x1b[39m (\x1b[39m\x1b[39;1m3.5.2\x1b[39;22m\x1b[39m)\x1b[39m: \x1b[34mInstalling...\x1b[39m",
        "\x1b[32;1m•\x1b[39;22m \x1b[39mInstalling \x1b[39m\x1b[36mpytest\x1b[39m\x1b[39m (\x1b[39m\x1b[32m3.5.2\x1b[39m\x1b[39m)\x1b[39m",  # finished
    ]
    output = io_decorated.fetch_output()
    # hint: use print(repr(output)) if you need to debug this

    for line in expected:
        assert line in output
    assert 0 == return_code


def test_execute_works_with_no_ansi_output(
    mocker, config, pool, io_not_decorated, tmp_dir, mock_file_downloads, env
):
    config = Config()
    config.merge({"cache-dir": tmp_dir})

    executor = Executor(env, pool, config, io_not_decorated)

    install_output = (
        "some string that does not contain a keyb0ard !nterrupt or cance11ed by u$er"
    )
    mocker.patch.object(env, "_run", return_value=install_output)
    return_code = executor.execute(
        [
            Install(Package("pytest", "3.5.2")),
        ]
    )
    env._run.assert_called_once()

    expected = """
Package operations: 1 install, 0 updates, 0 removals

  • Installing pytest (3.5.2)
"""
    expected = set(expected.splitlines())
    output = set(io_not_decorated.fetch_output().splitlines())
    assert expected == output
    assert 0 == return_code


def test_execute_should_show_operation_as_cancelled_on_subprocess_keyboard_interrupt(
    config, mocker, io, env
):
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


def test_execute_should_gracefully_handle_io_error(config, mocker, io, env):
    executor = Executor(env, pool, config, io)
    executor.verbose()

    original_write_line = executor._io.write_line

    def write_line(string, **kwargs):
        # Simulate UnicodeEncodeError
        string.encode("ascii")
        original_write_line(string, **kwargs)

    mocker.patch.object(io, "write_line", side_effect=write_line)

    assert 1 == executor.execute([Install(Package("clikit", "0.2.3"))])

    expected = r"""
Package operations: 1 install, 0 updates, 0 removals


\s*Unicode\w+Error
"""

    assert re.match(expected, io.fetch_output())


def test_executor_should_delete_incomplete_downloads(
    config, io, tmp_dir, mocker, pool, mock_file_downloads, env
):
    fixture = Path(__file__).parent.parent.joinpath(
        "fixtures/distributions/demo-0.1.0-py2.py3-none-any.whl"
    )
    destination_fixture = Path(tmp_dir) / "tomlkit-0.5.3-py2.py3-none-any.whl"
    shutil.copyfile(str(fixture), str(destination_fixture))
    mocker.patch(
        "poetry.installation.executor.Executor._download_archive",
        side_effect=Exception("Download error"),
    )
    mocker.patch(
        "poetry.installation.chef.Chef.get_cached_archive_for_link",
        side_effect=lambda link: link,
    )
    mocker.patch(
        "poetry.installation.chef.Chef.get_cache_directory_for_link",
        return_value=Path(tmp_dir),
    )

    config = Config()
    config.merge({"cache-dir": tmp_dir})

    executor = Executor(env, pool, config, io)

    with pytest.raises(Exception, match="Download error"):
        executor._download(Install(Package("tomlkit", "0.5.3")))

    assert not destination_fixture.exists()


def verify_installed_distribution(venv, package, url_reference=None):
    distributions = list(venv.site_packages.distributions(name=package.name))
    assert len(distributions) == 1

    distribution = distributions[0]
    metadata = distribution.metadata
    assert metadata["Name"] == package.name
    assert metadata["Version"] == package.version.text

    direct_url_file = distribution._path.joinpath("direct_url.json")

    if url_reference is not None:
        record_file = distribution._path.joinpath("RECORD")
        direct_url_entry = direct_url_file.relative_to(record_file.parent.parent)
        assert direct_url_file.exists()
        assert str(direct_url_entry) in {
            row.split(",")[0]
            for row in record_file.read_text(encoding="utf-8").splitlines()
        }
        assert json.loads(direct_url_file.read_text(encoding="utf-8")) == url_reference
    else:
        assert not direct_url_file.exists()


def test_executor_should_write_pep610_url_references_for_files(
    tmp_venv, pool, config, io
):
    url = (
        Path(__file__)
        .parent.parent.joinpath(
            "fixtures/distributions/demo-0.1.0-py2.py3-none-any.whl"
        )
        .resolve()
    )
    package = Package("demo", "0.1.0", source_type="file", source_url=url.as_posix())

    executor = Executor(tmp_venv, pool, config, io)
    executor.execute([Install(package)])
    verify_installed_distribution(
        tmp_venv, package, {"archive_info": {}, "url": url.as_uri()}
    )


def test_executor_should_write_pep610_url_references_for_directories(
    tmp_venv, pool, config, io
):
    url = Path(__file__).parent.parent.joinpath("fixtures/simple_project").resolve()
    package = Package(
        "simple-project", "1.2.3", source_type="directory", source_url=url.as_posix()
    )

    executor = Executor(tmp_venv, pool, config, io)
    executor.execute([Install(package)])
    verify_installed_distribution(
        tmp_venv, package, {"dir_info": {}, "url": url.as_uri()}
    )


def test_executor_should_write_pep610_url_references_for_editable_directories(
    tmp_venv, pool, config, io
):
    url = Path(__file__).parent.parent.joinpath("fixtures/simple_project").resolve()
    package = Package(
        "simple-project",
        "1.2.3",
        source_type="directory",
        source_url=url.as_posix(),
        develop=True,
    )

    executor = Executor(tmp_venv, pool, config, io)
    executor.execute([Install(package)])
    verify_installed_distribution(
        tmp_venv, package, {"dir_info": {"editable": True}, "url": url.as_uri()}
    )


def test_executor_should_write_pep610_url_references_for_urls(
    tmp_venv, pool, config, io, mock_file_downloads
):
    package = Package(
        "demo",
        "0.1.0",
        source_type="url",
        source_url="https://files.pythonhosted.org/demo-0.1.0-py2.py3-none-any.whl",
    )

    executor = Executor(tmp_venv, pool, config, io)
    executor.execute([Install(package)])
    verify_installed_distribution(
        tmp_venv, package, {"archive_info": {}, "url": package.source_url}
    )


def test_executor_should_write_pep610_url_references_for_git(
    tmp_venv, pool, config, io, mock_file_downloads
):
    package = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_reference="master",
        source_resolved_reference="123456",
        source_url="https://github.com/demo/demo.git",
    )

    executor = Executor(tmp_venv, pool, config, io)
    executor.execute([Install(package)])
    verify_installed_distribution(
        tmp_venv,
        package,
        {
            "vcs_info": {
                "vcs": "git",
                "requested_revision": "master",
                "commit_id": "123456",
            },
            "url": package.source_url,
        },
    )
