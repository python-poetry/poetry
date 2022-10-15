from __future__ import annotations

import csv
import json
import re
import shutil

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest

from cleo.formatters.style import Style
from cleo.io.buffered_io import BufferedIO
from poetry.core.packages.package import Package
from poetry.core.packages.utils.link import Link

from poetry.installation.executor import Executor
from poetry.installation.operations import Install
from poetry.installation.operations import Uninstall
from poetry.installation.operations import Update
from poetry.repositories.repository_pool import RepositoryPool
from poetry.utils.env import MockEnv
from tests.repositories.test_pypi_repository import MockRepository


if TYPE_CHECKING:
    import httpretty

    from httpretty.core import HTTPrettyRequest
    from pytest_mock import MockerFixture

    from poetry.config.config import Config
    from poetry.installation.operations.operation import Operation
    from poetry.utils.env import VirtualEnv
    from tests.types import FixtureDirGetter


@pytest.fixture
def env(tmp_dir: str) -> MockEnv:
    path = Path(tmp_dir) / ".venv"
    path.mkdir(parents=True)

    return MockEnv(path=path, is_venv=True)


@pytest.fixture()
def io() -> BufferedIO:
    io = BufferedIO()
    io.output.formatter.set_style("c1_dark", Style("cyan", options=["dark"]))
    io.output.formatter.set_style("c2_dark", Style("default", options=["bold", "dark"]))
    io.output.formatter.set_style("success_dark", Style("green", options=["dark"]))
    io.output.formatter.set_style("warning", Style("yellow"))

    return io


@pytest.fixture()
def io_decorated() -> BufferedIO:
    io = BufferedIO(decorated=True)
    io.output.formatter.set_style("c1", Style("cyan"))
    io.output.formatter.set_style("success", Style("green"))

    return io


@pytest.fixture()
def io_not_decorated() -> BufferedIO:
    io = BufferedIO(decorated=False)

    return io


@pytest.fixture()
def pool() -> RepositoryPool:
    pool = RepositoryPool()
    pool.add_repository(MockRepository())

    return pool


@pytest.fixture()
def mock_file_downloads(http: type[httpretty.httpretty]) -> None:
    def callback(
        request: HTTPrettyRequest, uri: str, headers: dict[str, Any]
    ) -> list[int | dict[str, Any] | str]:
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
    mocker: MockerFixture,
    config: Config,
    pool: RepositoryPool,
    io: BufferedIO,
    tmp_dir: str,
    mock_file_downloads: None,
    env: MockEnv,
):
    pip_install = mocker.patch("poetry.installation.executor.pip_install")

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
            Install(Package("pytest", "3.5.1")),
            Uninstall(Package("attrs", "17.4.0")),
            Update(Package("requests", "2.18.3"), Package("requests", "2.18.4")),
            Uninstall(Package("clikit", "0.2.3")).skip("Not currently installed"),
            Install(file_package),
            Install(directory_package),
            Install(git_package),
        ]
    )

    expected = f"""
Package operations: 4 installs, 1 update, 1 removal

  • Installing pytest (3.5.1)
  • Removing attrs (17.4.0)
  • Updating requests (2.18.3 -> 2.18.4)
  • Installing demo (0.1.0 {file_package.source_url})
  • Installing simple-project (1.2.3 {directory_package.source_url})
  • Installing demo (0.1.0 master)
"""

    expected = set(expected.splitlines())
    output = set(io.fetch_output().splitlines())
    assert output == expected
    assert len(env.executed) == 1
    assert return_code == 0
    assert pip_install.call_count == 5
    assert pip_install.call_args.kwargs.get("upgrade", False)
    assert pip_install.call_args.kwargs.get("editable", False)


@pytest.mark.parametrize(
    "operations, has_warning",
    [
        (
            [Install(Package("black", "21.11b0")), Install(Package("pytest", "3.5.1"))],
            True,
        ),
        (
            [
                Uninstall(Package("black", "21.11b0")),
                Uninstall(Package("pytest", "3.5.1")),
            ],
            False,
        ),
        (
            [
                Update(Package("black", "19.10b0"), Package("black", "21.11b0")),
                Update(Package("pytest", "3.5.0"), Package("pytest", "3.5.1")),
            ],
            True,
        ),
    ],
)
def test_execute_prints_warning_for_yanked_package(
    config: Config,
    pool: RepositoryPool,
    io: BufferedIO,
    tmp_dir: str,
    mock_file_downloads: None,
    env: MockEnv,
    operations: list[Operation],
    has_warning: bool,
):
    config.merge({"cache-dir": tmp_dir})

    executor = Executor(env, pool, config, io)

    return_code = executor.execute(operations)

    expected = (
        "Warning: The file chosen for install of black 21.11b0 "
        "(black-21.11b0-py3-none-any.whl) is yanked. Reason for being yanked: "
        "Broken regex dependency. Use 21.11b1 instead."
    )
    error = io.fetch_error()
    assert return_code == 0
    assert "pytest" not in error
    if has_warning:
        assert expected in error
        assert error.count("is yanked") == 1
    else:
        assert expected not in error
        assert error.count("yanked") == 0


def test_execute_shows_skipped_operations_if_verbose(
    config: Config,
    pool: RepositoryPool,
    io: BufferedIO,
    config_cache_dir: Path,
    env: MockEnv,
):
    config.merge({"cache-dir": config_cache_dir.as_posix()})

    executor = Executor(env, pool, config, io)
    executor.verbose()

    assert (
        executor.execute(
            [Uninstall(Package("clikit", "0.2.3")).skip("Not currently installed")]
        )
        == 0
    )

    expected = """
Package operations: 0 installs, 0 updates, 0 removals, 1 skipped

  • Removing clikit (0.2.3): Skipped for the following reason: Not currently installed
"""
    assert io.fetch_output() == expected
    assert len(env.executed) == 0


def test_execute_should_show_errors(
    config: Config,
    pool: RepositoryPool,
    mocker: MockerFixture,
    io: BufferedIO,
    env: MockEnv,
):
    executor = Executor(env, pool, config, io)
    executor.verbose()

    mocker.patch.object(executor, "_install", side_effect=Exception("It failed!"))

    assert executor.execute([Install(Package("clikit", "0.2.3"))]) == 1

    expected = """
Package operations: 1 install, 0 updates, 0 removals

  • Installing clikit (0.2.3)

  Exception

  It failed!
"""

    assert expected in io.fetch_output()


def test_execute_works_with_ansi_output(
    mocker: MockerFixture,
    config: Config,
    pool: RepositoryPool,
    io_decorated: BufferedIO,
    tmp_dir: str,
    mock_file_downloads: None,
    env: MockEnv,
):
    config.merge({"cache-dir": tmp_dir})

    executor = Executor(env, pool, config, io_decorated)

    install_output = (
        "some string that does not contain a keyb0ard !nterrupt or cance11ed by u$er"
    )
    mocker.patch.object(env, "_run", return_value=install_output)
    return_code = executor.execute(
        [
            Install(Package("pytest", "3.5.1")),
        ]
    )
    env._run.assert_called_once()

    # fmt: off
    expected = [
        "\x1b[39;1mPackage operations\x1b[39;22m: \x1b[34m1\x1b[39m install, \x1b[34m0\x1b[39m updates, \x1b[34m0\x1b[39m removals",  # noqa: E501
        "\x1b[34;1m•\x1b[39;22m \x1b[39mInstalling \x1b[39m\x1b[36mpytest\x1b[39m\x1b[39m (\x1b[39m\x1b[39;1m3.5.1\x1b[39;22m\x1b[39m)\x1b[39m: \x1b[34mPending...\x1b[39m",  # noqa: E501
        "\x1b[34;1m•\x1b[39;22m \x1b[39mInstalling \x1b[39m\x1b[36mpytest\x1b[39m\x1b[39m (\x1b[39m\x1b[39;1m3.5.1\x1b[39;22m\x1b[39m)\x1b[39m: \x1b[34mDownloading...\x1b[39m",  # noqa: E501
        "\x1b[34;1m•\x1b[39;22m \x1b[39mInstalling \x1b[39m\x1b[36mpytest\x1b[39m\x1b[39m (\x1b[39m\x1b[39;1m3.5.1\x1b[39;22m\x1b[39m)\x1b[39m: \x1b[34mInstalling...\x1b[39m",  # noqa: E501
        "\x1b[32;1m•\x1b[39;22m \x1b[39mInstalling \x1b[39m\x1b[36mpytest\x1b[39m\x1b[39m (\x1b[39m\x1b[32m3.5.1\x1b[39m\x1b[39m)\x1b[39m",  # finished  # noqa: E501
    ]
    # fmt: on

    output = io_decorated.fetch_output()
    # hint: use print(repr(output)) if you need to debug this

    for line in expected:
        assert line in output
    assert return_code == 0


def test_execute_works_with_no_ansi_output(
    mocker: MockerFixture,
    config: Config,
    pool: RepositoryPool,
    io_not_decorated: BufferedIO,
    tmp_dir: str,
    mock_file_downloads: None,
    env: MockEnv,
):
    config.merge({"cache-dir": tmp_dir})

    executor = Executor(env, pool, config, io_not_decorated)

    install_output = (
        "some string that does not contain a keyb0ard !nterrupt or cance11ed by u$er"
    )
    mocker.patch.object(env, "_run", return_value=install_output)
    return_code = executor.execute(
        [
            Install(Package("pytest", "3.5.1")),
        ]
    )
    env._run.assert_called_once()

    expected = """
Package operations: 1 install, 0 updates, 0 removals

  • Installing pytest (3.5.1)
"""
    expected = set(expected.splitlines())
    output = set(io_not_decorated.fetch_output().splitlines())
    assert output == expected
    assert return_code == 0


def test_execute_should_show_operation_as_cancelled_on_subprocess_keyboard_interrupt(
    config: Config,
    pool: RepositoryPool,
    mocker: MockerFixture,
    io: BufferedIO,
    env: MockEnv,
):
    executor = Executor(env, pool, config, io)
    executor.verbose()

    # A return code of -2 means KeyboardInterrupt in the pip subprocess
    mocker.patch.object(executor, "_install", return_value=-2)

    assert executor.execute([Install(Package("clikit", "0.2.3"))]) == 1

    expected = """
Package operations: 1 install, 0 updates, 0 removals

  • Installing clikit (0.2.3)
  • Installing clikit (0.2.3): Cancelled
"""

    assert io.fetch_output() == expected


def test_execute_should_gracefully_handle_io_error(
    config: Config,
    pool: RepositoryPool,
    mocker: MockerFixture,
    io: BufferedIO,
    env: MockEnv,
):
    executor = Executor(env, pool, config, io)
    executor.verbose()

    original_write_line = executor._io.write_line

    def write_line(string: str, **kwargs: Any) -> None:
        # Simulate UnicodeEncodeError
        string.encode("ascii")
        original_write_line(string, **kwargs)

    mocker.patch.object(io, "write_line", side_effect=write_line)

    assert executor.execute([Install(Package("clikit", "0.2.3"))]) == 1

    expected = r"""
Package operations: 1 install, 0 updates, 0 removals


\s*Unicode\w+Error
"""

    assert re.match(expected, io.fetch_output())


def test_executor_should_delete_incomplete_downloads(
    config: Config,
    io: BufferedIO,
    tmp_dir: str,
    mocker: MockerFixture,
    pool: RepositoryPool,
    mock_file_downloads: None,
    env: MockEnv,
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
        side_effect=lambda link: None,
    )
    mocker.patch(
        "poetry.installation.chef.Chef.get_cache_directory_for_link",
        return_value=Path(tmp_dir),
    )

    config.merge({"cache-dir": tmp_dir})

    executor = Executor(env, pool, config, io)

    with pytest.raises(Exception, match="Download error"):
        executor._download(Install(Package("tomlkit", "0.5.3")))

    assert not destination_fixture.exists()


def verify_installed_distribution(
    venv: VirtualEnv, package: Package, url_reference: dict[str, Any] | None = None
):
    distributions = list(venv.site_packages.distributions(name=package.name))
    assert len(distributions) == 1

    distribution = distributions[0]
    metadata = distribution.metadata
    assert metadata["Name"] == package.name
    assert metadata["Version"] == package.version.text

    direct_url_file = distribution._path.joinpath("direct_url.json")

    if url_reference is not None:
        record_file = distribution._path.joinpath("RECORD")
        with open(record_file, encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert all(len(row) == 3 for row in rows)
        record_entries = {row[0] for row in rows}
        direct_url_entry = direct_url_file.relative_to(record_file.parent.parent)
        assert direct_url_file.exists()
        assert str(direct_url_entry) in record_entries
        assert json.loads(direct_url_file.read_text(encoding="utf-8")) == url_reference
    else:
        assert not direct_url_file.exists()


@pytest.mark.parametrize(
    "package",
    [
        Package("demo", "0.1.0"),  # PyPI
        Package(  # private source
            "demo",
            "0.1.0",
            source_type="legacy",
            source_url="http://localhost:3141/root/pypi/+simple",
            source_reference="private",
        ),
    ],
)
def test_executor_should_not_write_pep610_url_references_for_cached_package(
    package: Package,
    mocker: MockerFixture,
    fixture_dir: FixtureDirGetter,
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    io: BufferedIO,
):
    link_cached = fixture_dir("distributions") / "demo-0.1.0-py2.py3-none-any.whl"

    mocker.patch(
        "poetry.installation.executor.Executor._download", return_value=link_cached
    )

    executor = Executor(tmp_venv, pool, config, io)
    executor.execute([Install(package)])
    verify_installed_distribution(tmp_venv, package)


def test_executor_should_write_pep610_url_references_for_files(
    tmp_venv: VirtualEnv, pool: RepositoryPool, config: Config, io: BufferedIO
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
    tmp_venv: VirtualEnv, pool: RepositoryPool, config: Config, io: BufferedIO
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
    tmp_venv: VirtualEnv, pool: RepositoryPool, config: Config, io: BufferedIO
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
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    io: BufferedIO,
    mock_file_downloads: None,
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
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    io: BufferedIO,
    mock_file_downloads: None,
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


def test_executor_should_write_pep610_url_references_for_git_with_subdirectories(
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    io: BufferedIO,
    mock_file_downloads: None,
):
    package = Package(
        "two",
        "2.0.0",
        source_type="git",
        source_reference="master",
        source_resolved_reference="123456",
        source_url="https://github.com/demo/subdirectories.git",
        source_subdirectory="two",
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
            "subdirectory": package.source_subdirectory,
        },
    )


def test_executor_should_use_cached_link_and_hash(
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    io: BufferedIO,
    mocker: MockerFixture,
    fixture_dir: FixtureDirGetter,
):
    link_cached = fixture_dir("distributions") / "demo-0.1.0-py2.py3-none-any.whl"

    mocker.patch(
        "poetry.installation.chef.Chef.get_cached_archive_for_link",
        return_value=link_cached,
    )

    package = Package("demo", "0.1.0")
    # Set package.files so the executor will attempt to hash the package
    package.files = [
        {
            "file": "demo-0.1.0-py2.py3-none-any.whl",
            "hash": "sha256:70e704135718fffbcbf61ed1fc45933cfd86951a744b681000eaaa75da31f17a",  # noqa: E501
        }
    ]

    executor = Executor(tmp_venv, pool, config, io)
    archive = executor._download_link(
        Install(package),
        Link("https://example.com/demo-0.1.0-py2.py3-none-any.whl"),
    )
    assert archive == link_cached


@pytest.mark.parametrize(
    ("max_workers", "cpu_count", "side_effect", "expected_workers"),
    [
        (None, 3, None, 7),
        (3, 4, None, 3),
        (8, 3, None, 7),
        (None, 8, NotImplementedError(), 5),
        (2, 8, NotImplementedError(), 2),
        (8, 8, NotImplementedError(), 5),
    ],
)
def test_executor_should_be_initialized_with_correct_workers(
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    io: BufferedIO,
    mocker: MockerFixture,
    max_workers: int | None,
    cpu_count: int | None,
    side_effect: Exception | None,
    expected_workers: int,
):
    config.merge({"installer": {"max-workers": max_workers}})

    mocker.patch("os.cpu_count", return_value=cpu_count, side_effect=side_effect)

    executor = Executor(tmp_venv, pool, config, io)

    assert executor._max_workers == expected_workers


def test_executer_fallback_on_poetry_create_error(
    mocker: MockerFixture,
    config: Config,
    pool: RepositoryPool,
    io: BufferedIO,
    tmp_dir: str,
    mock_file_downloads: None,
    env: MockEnv,
):
    mock_pip_install = mocker.patch("poetry.installation.executor.pip_install")
    mock_sdist_builder = mocker.patch("poetry.core.masonry.builders.sdist.SdistBuilder")
    mock_editable_builder = mocker.patch(
        "poetry.masonry.builders.editable.EditableBuilder"
    )
    mock_create_poetry = mocker.patch(
        "poetry.factory.Factory.create_poetry", side_effect=RuntimeError
    )

    config.merge({"cache-dir": tmp_dir})

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

    return_code = executor.execute(
        [
            Install(directory_package),
        ]
    )

    expected = f"""
Package operations: 1 install, 0 updates, 0 removals

  • Installing simple-project (1.2.3 {directory_package.source_url})
"""

    expected = set(expected.splitlines())
    output = set(io.fetch_output().splitlines())
    assert output == expected
    assert return_code == 0
    assert mock_create_poetry.call_count == 1
    assert mock_sdist_builder.call_count == 0
    assert mock_editable_builder.call_count == 0
    assert mock_pip_install.call_count == 1
    assert mock_pip_install.call_args[1].get("upgrade") is True
    assert mock_pip_install.call_args[1].get("editable") is False
