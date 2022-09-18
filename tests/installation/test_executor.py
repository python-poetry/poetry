from __future__ import annotations

import csv
import json
import re
import shutil
import tempfile

from pathlib import Path
from subprocess import CalledProcessError
from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from urllib.parse import urlparse

import pytest

from build import BuildBackendException
from build import ProjectBuilder
from cleo.formatters.style import Style
from cleo.io.buffered_io import BufferedIO
from cleo.io.outputs.output import Verbosity
from poetry.core.packages.package import Package
from poetry.core.packages.utils.link import Link

from poetry.factory import Factory
from poetry.installation.chef import Chef as BaseChef
from poetry.installation.executor import Executor
from poetry.installation.operations import Install
from poetry.installation.operations import Uninstall
from poetry.installation.operations import Update
from poetry.installation.wheel_installer import WheelInstaller
from poetry.repositories.pool import RepositoryPool
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


class Chef(BaseChef):
    _directory_wheels: list[Path] | None = None
    _sdist_wheels: list[Path] | None = None

    def set_directory_wheel(self, wheels: Path | list[Path]) -> None:
        if not isinstance(wheels, list):
            wheels = [wheels]

        self._directory_wheels = wheels

    def set_sdist_wheel(self, wheels: Path | list[Path]) -> None:
        if not isinstance(wheels, list):
            wheels = [wheels]

        self._sdist_wheels = wheels

    def _prepare_sdist(self, archive: Path, destination: Path | None = None) -> Path:
        if self._sdist_wheels is not None:
            wheel = self._sdist_wheels.pop(0)
            self._sdist_wheels.append(wheel)

            return wheel

        return super()._prepare_sdist(archive)

    def _prepare(
        self, directory: Path, destination: Path, *, editable: bool = False
    ) -> Path:
        if self._directory_wheels is not None:
            wheel = self._directory_wheels.pop(0)
            self._directory_wheels.append(wheel)

            return wheel

        return super()._prepare(directory, destination, editable=editable)


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
        name = Path(urlparse(uri).path).name

        fixture = Path(__file__).parent.parent.joinpath(
            "repositories/fixtures/pypi.org/dists/" + name
        )

        if not fixture.exists():
            fixture = Path(__file__).parent.parent.joinpath(
                "fixtures/distributions/demo-0.1.0-py2.py3-none-any.whl"
            )

        return [200, headers, fixture.read_bytes()]

    http.register_uri(
        http.GET,
        re.compile("^https://files.pythonhosted.org/.*$"),
        body=callback,
    )


@pytest.fixture()
def copy_wheel(tmp_dir: Path) -> Callable[[], Path]:
    def _copy_wheel() -> Path:
        tmp_name = tempfile.mktemp()
        Path(tmp_dir).joinpath(tmp_name).mkdir()

        shutil.copyfile(
            Path(__file__)
            .parent.parent.joinpath(
                "fixtures/distributions/demo-0.1.2-py2.py3-none-any.whl"
            )
            .as_posix(),
            Path(tmp_dir)
            .joinpath(tmp_name)
            .joinpath("demo-0.1.2-py2.py3-none-any.whl")
            .as_posix(),
        )

        return (
            Path(tmp_dir).joinpath(tmp_name).joinpath("demo-0.1.2-py2.py3-none-any.whl")
        )

    return _copy_wheel


@pytest.fixture()
def wheel(copy_wheel: Callable[[], Path]) -> Path:
    archive = copy_wheel()

    yield archive

    if archive.exists():
        archive.unlink()


def test_execute_executes_a_batch_of_operations(
    mocker: MockerFixture,
    config: Config,
    pool: RepositoryPool,
    io: BufferedIO,
    tmp_dir: str,
    mock_file_downloads: None,
    env: MockEnv,
    copy_wheel: Callable[[], Path],
):
    wheel_install = mocker.patch.object(WheelInstaller, "install")

    config.merge({"cache-dir": tmp_dir})

    prepare_spy = mocker.spy(Chef, "_prepare")
    chef = Chef(config, env)
    chef.set_directory_wheel([copy_wheel(), copy_wheel()])
    chef.set_sdist_wheel(copy_wheel())

    io.set_verbosity(Verbosity.VERY_VERBOSE)

    executor = Executor(env, pool, config, io)
    executor._chef = chef

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
    assert wheel_install.call_count == 5
    # Two pip uninstalls: one for the remove operation one for the update operation
    assert len(env.executed) == 2
    assert return_code == 0

    assert prepare_spy.call_count == 2
    assert prepare_spy.call_args_list == [
        mocker.call(chef, mocker.ANY, mocker.ANY, editable=False),
        mocker.call(chef, mocker.ANY, mocker.ANY, editable=True),
    ]


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
    output = io.fetch_output()
    error = io.fetch_error()
    assert return_code == 0, f"\noutput: {output}\nerror: {error}\n"
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
    config: Config,
    pool: RepositoryPool,
    io_decorated: BufferedIO,
    tmp_dir: str,
    mock_file_downloads: None,
    env: MockEnv,
):
    config.merge({"cache-dir": tmp_dir})

    executor = Executor(env, pool, config, io_decorated)

    return_code = executor.execute(
        [
            Install(Package("cleo", "1.0.0a5")),
        ]
    )

    # fmt: off
    expected = [
        "\x1b[39;1mPackage operations\x1b[39;22m: \x1b[34m1\x1b[39m install, \x1b[34m0\x1b[39m updates, \x1b[34m0\x1b[39m removals",  # noqa: E501
        "\x1b[34;1m•\x1b[39;22m \x1b[39mInstalling \x1b[39m\x1b[36mcleo\x1b[39m\x1b[39m (\x1b[39m\x1b[39;1m1.0.0a5\x1b[39;22m\x1b[39m)\x1b[39m: \x1b[34mPending...\x1b[39m",  # noqa: E501
        "\x1b[34;1m•\x1b[39;22m \x1b[39mInstalling \x1b[39m\x1b[36mcleo\x1b[39m\x1b[39m (\x1b[39m\x1b[39;1m1.0.0a5\x1b[39;22m\x1b[39m)\x1b[39m: \x1b[34mDownloading...\x1b[39m",  # noqa: E501
        "\x1b[34;1m•\x1b[39;22m \x1b[39mInstalling \x1b[39m\x1b[36mcleo\x1b[39m\x1b[39m (\x1b[39m\x1b[39;1m1.0.0a5\x1b[39;22m\x1b[39m)\x1b[39m: \x1b[34mInstalling...\x1b[39m",  # noqa: E501
        "\x1b[32;1m•\x1b[39;22m \x1b[39mInstalling \x1b[39m\x1b[36mcleo\x1b[39m\x1b[39m (\x1b[39m\x1b[32m1.0.0a5\x1b[39m\x1b[39m)\x1b[39m",  # finished  # noqa: E501
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

    return_code = executor.execute(
        [
            Install(Package("cleo", "1.0.0a5")),
        ]
    )

    expected = """
Package operations: 1 install, 0 updates, 0 removals

  • Installing cleo (1.0.0a5)
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
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    io: BufferedIO,
    wheel: Path,
):
    url = (
        Path(__file__)
        .parent.parent.joinpath("fixtures/git/github.com/demo/demo")
        .resolve()
    )
    package = Package(
        "demo", "0.1.2", source_type="directory", source_url=url.as_posix()
    )

    chef = Chef(config, tmp_venv)
    chef.set_directory_wheel(wheel)

    executor = Executor(tmp_venv, pool, config, io)
    executor._chef = chef
    executor.execute([Install(package)])
    verify_installed_distribution(
        tmp_venv, package, {"dir_info": {}, "url": url.as_uri()}
    )


def test_executor_should_write_pep610_url_references_for_editable_directories(
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    io: BufferedIO,
    wheel: Path,
):
    url = (
        Path(__file__)
        .parent.parent.joinpath("fixtures/git/github.com/demo/demo")
        .resolve()
    )
    package = Package(
        "demo",
        "0.1.2",
        source_type="directory",
        source_url=url.as_posix(),
        develop=True,
    )

    chef = Chef(config, tmp_venv)
    chef.set_directory_wheel(wheel)

    executor = Executor(tmp_venv, pool, config, io)
    executor._chef = chef
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
    wheel: Path,
):
    package = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_reference="master",
        source_resolved_reference="123456",
        source_url="https://github.com/demo/demo.git",
    )

    chef = Chef(config, tmp_venv)
    chef.set_directory_wheel(wheel)

    executor = Executor(tmp_venv, pool, config, io)
    executor._chef = chef
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
    wheel: Path,
):
    package = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_reference="master",
        source_resolved_reference="123456",
        source_url="https://github.com/demo/subdirectories.git",
        source_subdirectory="two",
    )

    chef = Chef(config, tmp_venv)
    chef.set_directory_wheel(wheel)

    executor = Executor(tmp_venv, pool, config, io)
    executor._chef = chef
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


def test_executor_fallback_on_poetry_create_error_without_wheel_installer(
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

    config.merge(
        {
            "cache-dir": tmp_dir,
            "installer": {"modern-installation": False},
        }
    )

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


@pytest.mark.parametrize("failing_method", ["build", "get_requires_for_build"])
def test_build_backend_errors_are_reported_correctly_if_caused_by_subprocess(
    failing_method: str,
    mocker: MockerFixture,
    config: Config,
    pool: RepositoryPool,
    io: BufferedIO,
    tmp_dir: str,
    mock_file_downloads: None,
    env: MockEnv,
):
    mocker.patch.object(Factory, "create_pool", return_value=pool)

    error = BuildBackendException(
        CalledProcessError(1, ["pip"], output=b"Error on stdout")
    )
    mocker.patch.object(ProjectBuilder, failing_method, side_effect=error)
    io.set_verbosity(Verbosity.NORMAL)

    executor = Executor(env, pool, config, io)

    package_name = "simple-project"
    package_version = "1.2.3"
    directory_package = Package(
        package_name,
        package_version,
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

    assert return_code == 1

    package_url = directory_package.source_url
    expected_start = f"""
Package operations: 1 install, 0 updates, 0 removals

  • Installing {package_name} ({package_version} {package_url})

  ChefBuildError

  Backend operation failed: CalledProcessError(1, ['pip'])
  \

  Error on stdout
"""

    requirement = directory_package.to_dependency().to_pep_508()
    expected_end = f"""
Note: This error originates from the build backend, and is likely not a problem with \
poetry but with {package_name} ({package_version} {package_url}) not supporting \
PEP 517 builds. You can verify this by running 'pip wheel --use-pep517 "{requirement}"'.

"""

    output = io.fetch_output()
    assert output.startswith(expected_start)
    assert output.endswith(expected_end)
