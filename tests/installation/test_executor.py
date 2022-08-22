# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import shutil

import pytest

from clikit.api.formatter.style import Style
from clikit.io.buffered_io import BufferedIO

from poetry.config.config import Config
from poetry.core.packages.package import Package
from poetry.core.packages.utils.link import Link
from poetry.installation.chef import Chef
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
        http.GET, re.compile("^https://files.pythonhosted.org/.*$"), body=callback,
    )


def test_execute_executes_a_batch_of_operations(
    config, pool, io, tmp_dir, mock_file_downloads
):
    config = Config()
    config.merge({"cache-dir": tmp_dir})

    env = MockEnv(path=Path(tmp_dir))
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
    )

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

    expected = set(expected.splitlines())
    output = set(io.fetch_output().splitlines())
    assert expected == output
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


def test_execute_should_gracefully_handle_io_error(config, mocker, io):
    env = MockEnv()
    executor = Executor(env, pool, config, io)
    executor.verbose()

    original_write_line = executor._io.write_line

    def write_line(string, flags=None):
        # Simulate UnicodeEncodeError
        string.encode("ascii")
        original_write_line(string, flags)

    mocker.patch.object(io, "write_line", side_effect=write_line)

    assert 1 == executor.execute([Install(Package("clikit", "0.2.3"))])

    expected = r"""
Package operations: 1 install, 0 updates, 0 removals


\s*Unicode\w+Error
"""

    assert re.match(expected, io.fetch_output())


def test_executor_should_delete_incomplete_downloads(
    config, io, tmp_dir, mocker, pool, mock_file_downloads
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

    env = MockEnv(path=Path(tmp_dir))
    executor = Executor(env, pool, config, io)

    with pytest.raises(Exception, match="Download error"):
        executor._download(Install(Package("tomlkit", "0.5.3")))

    assert not destination_fixture.exists()


def test_executor_should_check_every_possible_hash_types(
    config, io, pool, mocker, fixture_dir, tmp_dir
):
    mocker.patch.object(
        Chef, "get_cached_archive_for_link", side_effect=lambda link: link,
    )
    mocker.patch.object(
        Executor,
        "_download_archive",
        return_value=fixture_dir("distributions").joinpath(
            "demo-0.1.0-py2.py3-none-any.whl"
        ),
    )

    env = MockEnv(path=Path(tmp_dir))
    executor = Executor(env, pool, config, io)

    package = Package("demo", "0.1.0")
    package.files = [
        {
            "file": "demo-0.1.0-py2.py3-none-any.whl",
            "hash": "md5:15507846fd4299596661d0197bfb4f90",
        }
    ]

    archive = executor._download_link(
        Install(package), Link("https://example.com/demo-0.1.0-py2.py3-none-any.whl")
    )

    assert archive == fixture_dir("distributions").joinpath(
        "demo-0.1.0-py2.py3-none-any.whl"
    )


def test_executor_should_check_every_possible_hash_types_before_failing(
    config, io, pool, mocker, fixture_dir, tmp_dir
):
    mocker.patch.object(
        Chef, "get_cached_archive_for_link", side_effect=lambda link: link,
    )
    mocker.patch.object(
        Executor,
        "_download_archive",
        return_value=fixture_dir("distributions").joinpath(
            "demo-0.1.0-py2.py3-none-any.whl"
        ),
    )

    env = MockEnv(path=Path(tmp_dir))
    executor = Executor(env, pool, config, io)

    package = Package("demo", "0.1.0")
    package.files = [
        {"file": "demo-0.1.0-py2.py3-none-any.whl", "hash": "md5:123456"},
        {"file": "demo-0.1.0-py2.py3-none-any.whl", "hash": "sha256:123456"},
    ]

    expected_message = (
        "Invalid hashes "
        "("
        "md5:15507846fd4299596661d0197bfb4f90, "
        "sha256:70e704135718fffbcbf61ed1fc45933cfd86951a744b681000eaaa75da31f17a"
        ") "
        "for demo (0.1.0) using archive demo-0.1.0-py2.py3-none-any.whl. "
        "Expected one of md5:123456, sha256:123456."
    )

    with pytest.raises(RuntimeError, match=re.escape(expected_message)):
        executor._download_link(
            Install(package),
            Link("https://example.com/demo-0.1.0-py2.py3-none-any.whl"),
        )


def test_executor_should_use_cached_link_and_hash(
    config, io, pool, mocker, fixture_dir, tmp_dir
):
    # Produce a file:/// URI that is a valid link
    link_cached = Link(
        fixture_dir("distributions")
        .joinpath("demo-0.1.0-py2.py3-none-any.whl")
        .as_uri()
    )
    mocker.patch.object(
        Chef, "get_cached_archive_for_link", side_effect=lambda _: link_cached
    )

    env = MockEnv(path=Path(tmp_dir))
    executor = Executor(env, pool, config, io)

    package = Package("demo", "0.1.0")
    package.files = [
        {
            "file": "demo-0.1.0-py2.py3-none-any.whl",
            "hash": "md5:15507846fd4299596661d0197bfb4f90",
        }
    ]

    archive = executor._download_link(
        Install(package), Link("https://example.com/demo-0.1.0-py2.py3-none-any.whl")
    )

    assert archive == link_cached


def test_executer_fallback_on_poetry_create_error(
    mocker, config, pool, io, tmp_dir, mock_file_downloads,
):
    import poetry.installation.executor

    mock_pip_install = mocker.patch.object(
        poetry.installation.executor.Executor, "run_pip"
    )
    mock_sdist_builder = mocker.patch("poetry.core.masonry.builders.sdist.SdistBuilder")
    mock_editable_builder = mocker.patch(
        "poetry.masonry.builders.editable.EditableBuilder"
    )
    mock_create_poetry = mocker.patch(
        "poetry.factory.Factory.create_poetry", side_effect=RuntimeError
    )

    config.merge({"cache-dir": tmp_dir})

    env = MockEnv(path=Path(tmp_dir))
    executor = Executor(env, pool, config, io)

    directory_package = Package(
        "simple-project",
        "1.2.3",
        source_type="directory",
        source_url=Path(__file__)
        .parent.parent.joinpath("fixtures/simple_project")
        .resolve()
        .as_posix(),
    )

    return_code = executor.execute([Install(directory_package)])

    expected = """
Package operations: 1 install, 0 updates, 0 removals
  • Installing simple-project (1.2.3 {source_url})
""".format(
        source_url=directory_package.source_url
    )

    expected = set(expected.splitlines())
    output = set(io.fetch_output().splitlines())
    assert output == expected
    assert return_code == 0
    assert mock_create_poetry.call_count == 1
    assert mock_sdist_builder.call_count == 0
    assert mock_editable_builder.call_count == 0
    assert mock_pip_install.call_count == 1
