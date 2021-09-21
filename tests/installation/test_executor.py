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


try:
    from hashlib import algorithms_guaranteed as ALGORITHMS_GUARANTEED
except ImportError:
    ALGORITHMS_GUARANTEED = "md5,sha1,sha224,sha256,sha384,sha512".split(",")


@pytest.mark.parametrize(
    "hash_name,expected",
    [
        (hash_name, value)
        for hash_name, value in [
            ("sha224", "1c6ac3b371ed8af9c8db514f237c4c4696eca78c4766eb7a392c6205"),
            (
                "sha3_512",
                "6da91528a686799b0a8d3a582b5da50d0ae75eb45adf1f8f4b96b84279a777dc8fdfa4309972f859dbb343d6e69af6f367377a6fac75e1941dfc897fae6a9ff9",
            ),
            (
                "blake2s",
                "4508e2ff4a93b3ca4e0cd4b61348ddd2066a740c0a7c44692ad30eed3128ce12",
            ),
            (
                "sha3_384",
                "2a0e744f2d15938e35bf1d0350edf8f03f9dc507bee74dc9823626d72210c4d0df4099fc9ba70133f7f72d6e7d2ea598",
            ),
            (
                "blake2b",
                "211843c91d73a96e584bddf3e1b9e6915903a98daf36b181643b20590af1fe3a8cc62856e42126c34f89f293cf836c41e27af29a97678744ef9f1a56f10f89ad",
            ),
            (
                "sha256",
                "70e704135718fffbcbf61ed1fc45933cfd86951a744b681000eaaa75da31f17a",
            ),
            (
                "sha512",
                "44cfa6b8696e5008c1c4dfe32c52a8b6511c261d8f3a25882366c0718eb42a17da5e4b9196623597661871be65c48e613d8f5c50a5c5c827e0efbf8b612fe5be",
            ),
            (
                "sha384",
                "55daa98dcf37a699df770a9c94c4ee50dd155137152c018fcbaa607d879e24b50abb6fd19d7a4f8b5ef0ae7ecf0359dc",
            ),
            ("sha3_224", "757f3dfe2159e25e3994e8935604448d25d11bf99b9730663ca85cc9"),
            ("sha1", "24ad37bd0efbb1e66ed888a3429ad13a717b2ec4"),
            (
                "sha3_256",
                "a5acd9ee8f486b3d6b4a7c4b9f65ec0915028c91997ff0a55cd5fcc4322a5da8",
            ),
        ]
        if hash_name in ALGORITHMS_GUARANTEED
    ],
)
def test_download_link_checks_hash(
    config, pool, io, tmp_dir, mock_file_downloads, hash_name, expected
):
    config = Config()
    config.merge({"cache-dir": tmp_dir})

    env = MockEnv(path=Path(tmp_dir))

    executor = Executor(env, pool, config, io)

    sha_package = Package(name="demo", version="0.1.0",)

    sha_package.files.append(
        {
            "file": "demo-0.1.0-py2.py3-none-any.whl",
            "hash": "{}:{}".format(hash_name, expected),
        }
    )

    install_operation = Install(sha_package)
    link = Link("https://files.pythonhosted.org/simple/demo-0.1.0-py2.py3-none-any.whl")

    # Test that this works without exception
    executor._download_link(install_operation, link)

    # Then spoil the hash and check that it fails
    def ruin_hash(hash):
        return hash[1:] + hash[0]

    sha_package = Package(name="demo", version="0.1.0",)

    sha_package.files.append(
        {
            "file": "demo-0.1.0-py2.py3-none-any.whl",
            "hash": "{}:{}".format(hash_name, ruin_hash(expected)),
        }
    )

    install_operation = Install(sha_package)
    link = Link("https://files.pythonhosted.org/simple/demo-0.1.0-py2.py3-none-any.whl")

    with pytest.raises(
        RuntimeError,
        match="Invalid {} hash for demo \\(0.1.0\\) using file demo-0.1.0-py2.py3-none-any.whl".format(
            hash_name
        ),
    ):
        executor._download_link(install_operation, link)


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
