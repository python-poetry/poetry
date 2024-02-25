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

import pytest

from build import BuildBackendException
from build import ProjectBuilder
from cleo.formatters.style import Style
from cleo.io.buffered_io import BufferedIO
from cleo.io.outputs.output import Verbosity
from poetry.core.packages.package import Package
from poetry.core.packages.utils.utils import path_to_url

from poetry.factory import Factory
from poetry.installation.chef import Chef as BaseChef
from poetry.installation.executor import Executor
from poetry.installation.operations import Install
from poetry.installation.operations import Uninstall
from poetry.installation.operations import Update
from poetry.installation.wheel_installer import WheelInstaller
from poetry.repositories.repository_pool import RepositoryPool
from poetry.utils.cache import ArtifactCache
from poetry.utils.env import MockEnv
from poetry.vcs.git.backend import Git
from tests.repositories.test_pypi_repository import MockRepository


if TYPE_CHECKING:
    from collections.abc import Iterator

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

            destination.mkdir(parents=True, exist_ok=True)
            dst_wheel = destination / wheel.name
            shutil.copyfile(wheel, dst_wheel)
            return dst_wheel

        return super()._prepare(directory, destination, editable=editable)


@pytest.fixture
def env(tmp_path: Path) -> MockEnv:
    path = tmp_path / ".venv"
    path.mkdir(parents=True)

    return MockEnv(path=path, is_venv=True)


@pytest.fixture
def io() -> BufferedIO:
    io = BufferedIO()
    io.output.formatter.set_style("c1_dark", Style("cyan", options=["dark"]))
    io.output.formatter.set_style("c2_dark", Style("default", options=["bold", "dark"]))
    io.output.formatter.set_style("success_dark", Style("green", options=["dark"]))
    io.output.formatter.set_style("warning", Style("yellow"))

    return io


@pytest.fixture
def io_decorated() -> BufferedIO:
    io = BufferedIO(decorated=True)
    io.output.formatter.set_style("c1", Style("cyan"))
    io.output.formatter.set_style("success", Style("green"))

    return io


@pytest.fixture
def io_not_decorated() -> BufferedIO:
    io = BufferedIO(decorated=False)

    return io


@pytest.fixture
def pool() -> RepositoryPool:
    pool = RepositoryPool()
    pool.add_repository(MockRepository())

    return pool


@pytest.fixture
def copy_wheel(tmp_path: Path, fixture_dir: FixtureDirGetter) -> Callable[[], Path]:
    def _copy_wheel() -> Path:
        tmp_name = tempfile.mktemp()
        (tmp_path / tmp_name).mkdir()

        shutil.copyfile(
            fixture_dir("distributions") / "demo-0.1.2-py2.py3-none-any.whl",
            tmp_path / tmp_name / "demo-0.1.2-py2.py3-none-any.whl",
        )
        return tmp_path / tmp_name / "demo-0.1.2-py2.py3-none-any.whl"

    return _copy_wheel


@pytest.fixture
def wheel(copy_wheel: Callable[[], Path]) -> Iterator[Path]:
    archive = copy_wheel()

    yield archive

    if archive.exists():
        archive.unlink()


def test_execute_executes_a_batch_of_operations(
    mocker: MockerFixture,
    config: Config,
    pool: RepositoryPool,
    io: BufferedIO,
    tmp_path: Path,
    mock_file_downloads: None,
    env: MockEnv,
    copy_wheel: Callable[[], Path],
    fixture_dir: FixtureDirGetter,
) -> None:
    wheel_install = mocker.patch.object(WheelInstaller, "install")

    config.merge({"cache-dir": str(tmp_path)})
    artifact_cache = ArtifactCache(cache_dir=config.artifacts_cache_directory)

    prepare_spy = mocker.spy(Chef, "_prepare")
    chef = Chef(artifact_cache, env, Factory.create_pool(config))
    chef.set_directory_wheel([copy_wheel(), copy_wheel()])
    chef.set_sdist_wheel(copy_wheel())

    io.set_verbosity(Verbosity.VERY_VERBOSE)

    executor = Executor(env, pool, config, io)
    executor._chef = chef

    file_package = Package(
        "demo",
        "0.1.0",
        source_type="file",
        source_url=(fixture_dir("distributions") / "demo-0.1.0-py2.py3-none-any.whl")
        .resolve()
        .as_posix(),
    )

    directory_package = Package(
        "simple-project",
        "1.2.3",
        source_type="directory",
        source_url=fixture_dir("simple_project").resolve().as_posix(),
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
            Update(Package("pytest", "3.5.1"), Package("pytest", "3.5.0")),
            Uninstall(Package("clikit", "0.2.3")).skip("Not currently installed"),
            Install(file_package),
            Install(directory_package),
            Install(git_package),
        ]
    )

    expected = f"""
Package operations: 4 installs, 2 updates, 1 removal

  - Installing pytest (3.5.1)
  - Removing attrs (17.4.0)
  - Updating requests (2.18.3 -> 2.18.4)
  - Downgrading pytest (3.5.1 -> 3.5.0)
  - Installing demo (0.1.0 {file_package.source_url})
  - Installing simple-project (1.2.3 {directory_package.source_url})
  - Installing demo (0.1.0 master)
"""

    expected_lines = set(expected.splitlines())
    output_lines = set(io.fetch_output().splitlines())
    assert output_lines == expected_lines
    assert wheel_install.call_count == 6
    # 3 pip uninstalls: one for the remove operation and two for the update operations
    assert len(env.executed) == 3
    assert return_code == 0

    assert prepare_spy.call_count == 2
    assert prepare_spy.call_args_list == [
        mocker.call(chef, mocker.ANY, destination=mocker.ANY, editable=False),
        mocker.call(chef, mocker.ANY, destination=mocker.ANY, editable=True),
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
    tmp_path: Path,
    mock_file_downloads: None,
    env: MockEnv,
    operations: list[Operation],
    has_warning: bool,
) -> None:
    config.merge({"cache-dir": str(tmp_path)})

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


@pytest.mark.skip(reason="https://github.com/python-poetry/poetry/issues/7983")
def test_execute_prints_warning_for_invalid_wheels(
    config: Config,
    pool: RepositoryPool,
    io: BufferedIO,
    tmp_path: Path,
    mock_file_downloads: None,
    env: MockEnv,
) -> None:
    config.merge({"cache-dir": str(tmp_path)})

    executor = Executor(env, pool, config, io)

    base_url = "https://files.pythonhosted.org/"
    wheel1 = "demo_invalid_record-0.1.0-py2.py3-none-any.whl"
    wheel2 = "demo_invalid_record2-0.1.0-py2.py3-none-any.whl"
    return_code = executor.execute(
        [
            Install(
                Package(
                    "demo-invalid-record",
                    "0.1.0",
                    source_type="url",
                    source_url=f"{base_url}/{wheel1}",
                )
            ),
            Install(
                Package(
                    "demo-invalid-record2",
                    "0.1.0",
                    source_type="url",
                    source_url=f"{base_url}/{wheel2}",
                )
            ),
        ]
    )

    warning1 = f"""\
<warning>Warning: Validation of the RECORD file of {wheel1} failed.\
 Please report to the maintainers of that package so they can fix their build process.\
 Details:
In .*?{wheel1}, demo/__init__.py is not mentioned in RECORD
In .*?{wheel1}, demo_invalid_record-0.1.0.dist-info/WHEEL is not mentioned in RECORD
"""

    warning2 = f"""\
<warning>Warning: Validation of the RECORD file of {wheel2} failed.\
 Please report to the maintainers of that package so they can fix their build process.\
 Details:
In .*?{wheel2}, hash / size of demo_invalid_record2-0.1.0.dist-info/METADATA didn't\
 match RECORD
"""

    output = io.fetch_output()
    error = io.fetch_error()
    assert return_code == 0, f"\noutput: {output}\nerror: {error}\n"
    assert re.match(f"{warning1}\n{warning2}", error) or re.match(
        f"{warning2}\n{warning1}", error
    ), error


def test_execute_shows_skipped_operations_if_verbose(
    config: Config,
    pool: RepositoryPool,
    io: BufferedIO,
    config_cache_dir: Path,
    env: MockEnv,
) -> None:
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

  - Removing clikit (0.2.3): Skipped for the following reason: Not currently installed
"""
    assert io.fetch_output() == expected
    assert len(env.executed) == 0


def test_execute_should_show_errors(
    config: Config,
    pool: RepositoryPool,
    mocker: MockerFixture,
    io: BufferedIO,
    env: MockEnv,
) -> None:
    executor = Executor(env, pool, config, io)
    executor.verbose()

    mocker.patch.object(executor, "_install", side_effect=Exception("It failed!"))

    assert executor.execute([Install(Package("clikit", "0.2.3"))]) == 1

    expected = """
Package operations: 1 install, 0 updates, 0 removals

  - Installing clikit (0.2.3)

  Exception

  It failed!
"""

    assert expected in io.fetch_output()


def test_execute_works_with_ansi_output(
    config: Config,
    pool: RepositoryPool,
    io_decorated: BufferedIO,
    tmp_path: Path,
    mock_file_downloads: None,
    env: MockEnv,
) -> None:
    config.merge({"cache-dir": str(tmp_path)})

    executor = Executor(env, pool, config, io_decorated)

    return_code = executor.execute(
        [
            Install(Package("cleo", "1.0.0a5")),
        ]
    )

    # fmt: off
    expected = [
        "\x1b[39;1mPackage operations\x1b[39;22m: \x1b[34m1\x1b[39m install, \x1b[34m0\x1b[39m updates, \x1b[34m0\x1b[39m removals",
        "\x1b[34;1m-\x1b[39;22m \x1b[39mInstalling \x1b[39m\x1b[36mcleo\x1b[39m\x1b[39m (\x1b[39m\x1b[39;1m1.0.0a5\x1b[39;22m\x1b[39m)\x1b[39m: \x1b[34mPending...\x1b[39m",
        "\x1b[34;1m-\x1b[39;22m \x1b[39mInstalling \x1b[39m\x1b[36mcleo\x1b[39m\x1b[39m (\x1b[39m\x1b[39;1m1.0.0a5\x1b[39;22m\x1b[39m)\x1b[39m: \x1b[34mDownloading...\x1b[39m",
        "\x1b[34;1m-\x1b[39;22m \x1b[39mInstalling \x1b[39m\x1b[36mcleo\x1b[39m\x1b[39m (\x1b[39m\x1b[39;1m1.0.0a5\x1b[39;22m\x1b[39m)\x1b[39m: \x1b[34mInstalling...\x1b[39m",
        "\x1b[32;1m-\x1b[39;22m \x1b[39mInstalling \x1b[39m\x1b[36mcleo\x1b[39m\x1b[39m (\x1b[39m\x1b[32m1.0.0a5\x1b[39m\x1b[39m)\x1b[39m",  # finished
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
    tmp_path: Path,
    mock_file_downloads: None,
    env: MockEnv,
) -> None:
    config.merge({"cache-dir": str(tmp_path)})

    executor = Executor(env, pool, config, io_not_decorated)

    return_code = executor.execute(
        [
            Install(Package("cleo", "1.0.0a5")),
        ]
    )

    expected = """
Package operations: 1 install, 0 updates, 0 removals

  - Installing cleo (1.0.0a5)
"""
    expected_lines = set(expected.splitlines())
    output_lines = set(io_not_decorated.fetch_output().splitlines())
    assert output_lines == expected_lines
    assert return_code == 0


def test_execute_should_show_operation_as_cancelled_on_subprocess_keyboard_interrupt(
    config: Config,
    pool: RepositoryPool,
    mocker: MockerFixture,
    io: BufferedIO,
    env: MockEnv,
) -> None:
    executor = Executor(env, pool, config, io)
    executor.verbose()

    # A return code of -2 means KeyboardInterrupt in the pip subprocess
    mocker.patch.object(executor, "_install", return_value=-2)

    assert executor.execute([Install(Package("clikit", "0.2.3"))]) == 1

    expected = """
Package operations: 1 install, 0 updates, 0 removals

  - Installing clikit (0.2.3)
  - Installing clikit (0.2.3): Cancelled
"""

    assert io.fetch_output() == expected


def test_execute_should_gracefully_handle_io_error(
    config: Config,
    pool: RepositoryPool,
    mocker: MockerFixture,
    io: BufferedIO,
    env: MockEnv,
) -> None:
    executor = Executor(env, pool, config, io)
    executor.verbose()

    original_write_line = executor._io.write_line

    def write_line(string: str, **kwargs: Any) -> None:
        # Simulate UnicodeEncodeError
        string = string.replace("-", "•")
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
    tmp_path: Path,
    mocker: MockerFixture,
    pool: RepositoryPool,
    mock_file_downloads: None,
    env: MockEnv,
) -> None:
    cached_archive = tmp_path / "tomlkit-0.5.3-py2.py3-none-any.whl"

    def download_fail(*_: Any) -> None:
        cached_archive.touch()  # broken archive
        raise Exception("Download error")

    mocker.patch(
        "poetry.installation.executor.Executor._download_archive",
        side_effect=download_fail,
    )
    mocker.patch(
        "poetry.utils.cache.ArtifactCache._get_cached_archive",
        return_value=None,
    )
    mocker.patch(
        "poetry.utils.cache.ArtifactCache.get_cache_directory_for_link",
        return_value=tmp_path,
    )

    config.merge({"cache-dir": str(tmp_path)})

    executor = Executor(env, pool, config, io)

    with pytest.raises(Exception, match="Download error"):
        executor._download(Install(Package("tomlkit", "0.5.3")))

    assert not cached_archive.exists()


def verify_installed_distribution(
    venv: VirtualEnv, package: Package, url_reference: dict[str, Any] | None = None
) -> None:
    distributions = list(venv.site_packages.distributions(name=package.name))
    assert len(distributions) == 1

    distribution = distributions[0]
    metadata = distribution.metadata
    assert metadata["Name"] == package.name
    assert metadata["Version"] == package.version.text

    direct_url_file = distribution._path.joinpath(  # type: ignore[attr-defined]
        "direct_url.json"
    )

    if url_reference is not None:
        record_file = distribution._path.joinpath(  # type: ignore[attr-defined]
            "RECORD"
        )
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
) -> None:
    link_cached = fixture_dir("distributions") / "demo-0.1.0-py2.py3-none-any.whl"
    package.files = [
        {
            "file": "demo-0.1.0-py2.py3-none-any.whl",
            "hash": (
                "sha256:70e704135718fffbcbf61ed1fc45933cfd86951a744b681000eaaa75da31f17a"
            ),
        }
    ]

    mocker.patch(
        "poetry.installation.executor.Executor._download", return_value=link_cached
    )

    executor = Executor(tmp_venv, pool, config, io)
    executor.execute([Install(package)])
    verify_installed_distribution(tmp_venv, package)
    assert link_cached.exists(), "cached file should not be deleted"


def test_executor_should_write_pep610_url_references_for_wheel_files(
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    io: BufferedIO,
    fixture_dir: FixtureDirGetter,
) -> None:
    url = (fixture_dir("distributions") / "demo-0.1.0-py2.py3-none-any.whl").resolve()
    package = Package("demo", "0.1.0", source_type="file", source_url=url.as_posix())
    # Set package.files so the executor will attempt to hash the package
    package.files = [
        {
            "file": "demo-0.1.0-py2.py3-none-any.whl",
            "hash": (
                "sha256:70e704135718fffbcbf61ed1fc45933cfd86951a744b681000eaaa75da31f17a"
            ),
        }
    ]

    executor = Executor(tmp_venv, pool, config, io)
    executor.execute([Install(package)])
    expected_url_reference = {
        "archive_info": {
            "hashes": {
                "sha256": (
                    "70e704135718fffbcbf61ed1fc45933cfd86951a744b681000eaaa75da31f17a"
                )
            },
        },
        "url": url.as_uri(),
    }
    verify_installed_distribution(tmp_venv, package, expected_url_reference)
    assert url.exists(), "source file should not be deleted"


def test_executor_should_write_pep610_url_references_for_non_wheel_files(
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    io: BufferedIO,
    fixture_dir: FixtureDirGetter,
    mock_file_downloads: None,
) -> None:
    url = (fixture_dir("distributions") / "demo-0.1.0.tar.gz").resolve()
    package = Package("demo", "0.1.0", source_type="file", source_url=url.as_posix())
    # Set package.files so the executor will attempt to hash the package
    package.files = [
        {
            "file": "demo-0.1.0.tar.gz",
            "hash": (
                "sha256:9fa123ad707a5c6c944743bf3e11a0e80d86cb518d3cf25320866ca3ef43e2ad"
            ),
        }
    ]

    executor = Executor(tmp_venv, pool, config, io)
    executor.execute([Install(package)])
    expected_url_reference = {
        "archive_info": {
            "hashes": {
                "sha256": (
                    "9fa123ad707a5c6c944743bf3e11a0e80d86cb518d3cf25320866ca3ef43e2ad"
                )
            },
        },
        "url": url.as_uri(),
    }
    verify_installed_distribution(tmp_venv, package, expected_url_reference)
    assert url.exists(), "source file should not be deleted"


def test_executor_should_write_pep610_url_references_for_directories(
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    artifact_cache: ArtifactCache,
    io: BufferedIO,
    wheel: Path,
    fixture_dir: FixtureDirGetter,
    mocker: MockerFixture,
) -> None:
    url = (fixture_dir("git") / "github.com" / "demo" / "demo").resolve()
    package = Package(
        "demo", "0.1.2", source_type="directory", source_url=url.as_posix()
    )

    chef = Chef(artifact_cache, tmp_venv, Factory.create_pool(config))
    chef.set_directory_wheel(wheel)
    prepare_spy = mocker.spy(chef, "prepare")

    executor = Executor(tmp_venv, pool, config, io)
    executor._chef = chef
    executor.execute([Install(package)])
    verify_installed_distribution(
        tmp_venv, package, {"dir_info": {}, "url": url.as_uri()}
    )
    assert not prepare_spy.spy_return.exists(), "archive not cleaned up"


def test_executor_should_write_pep610_url_references_for_editable_directories(
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    artifact_cache: ArtifactCache,
    io: BufferedIO,
    wheel: Path,
    fixture_dir: FixtureDirGetter,
    mocker: MockerFixture,
) -> None:
    url = (fixture_dir("git") / "github.com" / "demo" / "demo").resolve()
    package = Package(
        "demo",
        "0.1.2",
        source_type="directory",
        source_url=url.as_posix(),
        develop=True,
    )

    chef = Chef(artifact_cache, tmp_venv, Factory.create_pool(config))
    chef.set_directory_wheel(wheel)
    prepare_spy = mocker.spy(chef, "prepare")

    executor = Executor(tmp_venv, pool, config, io)
    executor._chef = chef
    executor.execute([Install(package)])
    verify_installed_distribution(
        tmp_venv, package, {"dir_info": {"editable": True}, "url": url.as_uri()}
    )
    assert not prepare_spy.spy_return.exists(), "archive not cleaned up"


@pytest.mark.parametrize("is_artifact_cached", [False, True])
def test_executor_should_write_pep610_url_references_for_wheel_urls(
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    io: BufferedIO,
    mock_file_downloads: None,
    mocker: MockerFixture,
    fixture_dir: FixtureDirGetter,
    is_artifact_cached: bool,
) -> None:
    if is_artifact_cached:
        link_cached = fixture_dir("distributions") / "demo-0.1.0-py2.py3-none-any.whl"
        mocker.patch(
            "poetry.utils.cache.ArtifactCache.get_cached_archive_for_link",
            return_value=link_cached,
        )
    download_spy = mocker.spy(Executor, "_download_archive")

    package = Package(
        "demo",
        "0.1.0",
        source_type="url",
        source_url="https://files.pythonhosted.org/demo-0.1.0-py2.py3-none-any.whl",
    )
    # Set package.files so the executor will attempt to hash the package
    package.files = [
        {
            "file": "demo-0.1.0-py2.py3-none-any.whl",
            "hash": (
                "sha256:70e704135718fffbcbf61ed1fc45933cfd86951a744b681000eaaa75da31f17a"
            ),
        }
    ]

    executor = Executor(tmp_venv, pool, config, io)
    operation = Install(package)
    executor.execute([operation])
    expected_url_reference = {
        "archive_info": {
            "hashes": {
                "sha256": (
                    "70e704135718fffbcbf61ed1fc45933cfd86951a744b681000eaaa75da31f17a"
                )
            },
        },
        "url": package.source_url,
    }
    verify_installed_distribution(tmp_venv, package, expected_url_reference)
    if is_artifact_cached:
        download_spy.assert_not_called()
    else:
        assert package.source_url is not None
        download_spy.assert_called_once_with(
            mocker.ANY,
            operation,
            package.source_url,
            dest=mocker.ANY,
        )
        dest = download_spy.call_args.args[3]
        assert dest.exists(), "cached file should not be deleted"


@pytest.mark.parametrize(
    (
        "is_sdist_cached",
        "is_wheel_cached",
        "expect_artifact_building",
        "expect_artifact_download",
    ),
    [
        (True, False, True, False),
        (True, True, False, False),
        (False, False, True, True),
        (False, True, False, True),
    ],
)
def test_executor_should_write_pep610_url_references_for_non_wheel_urls(
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    io: BufferedIO,
    mock_file_downloads: None,
    mocker: MockerFixture,
    fixture_dir: FixtureDirGetter,
    is_sdist_cached: bool,
    is_wheel_cached: bool,
    expect_artifact_building: bool,
    expect_artifact_download: bool,
) -> None:
    built_wheel = fixture_dir("distributions") / "demo-0.1.0-py2.py3-none-any.whl"
    mock_prepare = mocker.patch(
        "poetry.installation.chef.Chef._prepare",
        return_value=built_wheel,
    )
    download_spy = mocker.spy(Executor, "_download_archive")

    if is_sdist_cached or is_wheel_cached:
        cached_sdist = fixture_dir("distributions") / "demo-0.1.0.tar.gz"
        cached_wheel = fixture_dir("distributions") / "demo-0.1.0-py2.py3-none-any.whl"

        def mock_get_cached_archive_func(
            _cache_dir: Path, *, strict: bool, **__: Any
        ) -> Path | None:
            if is_wheel_cached and not strict:
                return cached_wheel
            if is_sdist_cached:
                return cached_sdist
            return None

        mocker.patch(
            "poetry.utils.cache.ArtifactCache._get_cached_archive",
            side_effect=mock_get_cached_archive_func,
        )

    package = Package(
        "demo",
        "0.1.0",
        source_type="url",
        source_url="https://files.pythonhosted.org/demo-0.1.0.tar.gz",
    )
    # Set package.files so the executor will attempt to hash the package
    package.files = [
        {
            "file": "demo-0.1.0.tar.gz",
            "hash": (
                "sha256:9fa123ad707a5c6c944743bf3e11a0e80d86cb518d3cf25320866ca3ef43e2ad"
            ),
        }
    ]

    executor = Executor(tmp_venv, pool, config, io)
    operation = Install(package)
    executor.execute([operation])
    expected_url_reference = {
        "archive_info": {
            "hashes": {
                "sha256": (
                    "9fa123ad707a5c6c944743bf3e11a0e80d86cb518d3cf25320866ca3ef43e2ad"
                )
            },
        },
        "url": package.source_url,
    }
    verify_installed_distribution(tmp_venv, package, expected_url_reference)

    if expect_artifact_building:
        mock_prepare.assert_called_once()
    else:
        mock_prepare.assert_not_called()

    if expect_artifact_download:
        assert package.source_url is not None
        download_spy.assert_called_once_with(
            mocker.ANY, operation, package.source_url, dest=mocker.ANY
        )
        dest = download_spy.call_args.args[3]
        assert dest.exists(), "cached file should not be deleted"
    else:
        download_spy.assert_not_called()


@pytest.mark.parametrize("is_artifact_cached", [False, True])
def test_executor_should_write_pep610_url_references_for_git(
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    artifact_cache: ArtifactCache,
    io: BufferedIO,
    mock_file_downloads: None,
    wheel: Path,
    mocker: MockerFixture,
    fixture_dir: FixtureDirGetter,
    is_artifact_cached: bool,
) -> None:
    if is_artifact_cached:
        link_cached = fixture_dir("distributions") / "demo-0.1.2-py2.py3-none-any.whl"
        mocker.patch(
            "poetry.utils.cache.ArtifactCache.get_cached_archive_for_git",
            return_value=link_cached,
        )
    clone_spy = mocker.spy(Git, "clone")

    source_resolved_reference = "123456"
    source_url = "https://github.com/demo/demo.git"

    package = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_reference="master",
        source_resolved_reference=source_resolved_reference,
        source_url=source_url,
    )

    chef = Chef(artifact_cache, tmp_venv, Factory.create_pool(config))
    chef.set_directory_wheel(wheel)
    prepare_spy = mocker.spy(chef, "prepare")

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

    if is_artifact_cached:
        clone_spy.assert_not_called()
        prepare_spy.assert_not_called()
    else:
        clone_spy.assert_called_once_with(
            url=source_url, source_root=mocker.ANY, revision=source_resolved_reference
        )
        prepare_spy.assert_called_once()
        assert prepare_spy.spy_return.exists(), "cached file should not be deleted"
        assert (prepare_spy.spy_return.parent / ".created_from_git_dependency").exists()


def test_executor_should_write_pep610_url_references_for_editable_git(
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    artifact_cache: ArtifactCache,
    io: BufferedIO,
    mock_file_downloads: None,
    wheel: Path,
    mocker: MockerFixture,
    fixture_dir: FixtureDirGetter,
) -> None:
    source_resolved_reference = "123456"
    source_url = "https://github.com/demo/demo.git"

    package = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_reference="master",
        source_resolved_reference=source_resolved_reference,
        source_url=source_url,
        develop=True,
    )

    chef = Chef(artifact_cache, tmp_venv, Factory.create_pool(config))
    chef.set_directory_wheel(wheel)
    prepare_spy = mocker.spy(chef, "prepare")
    cache_spy = mocker.spy(artifact_cache, "get_cached_archive_for_git")

    executor = Executor(tmp_venv, pool, config, io)
    executor._chef = chef
    executor.execute([Install(package)])
    assert package.source_url is not None
    verify_installed_distribution(
        tmp_venv,
        package,
        {
            "dir_info": {"editable": True},
            "url": Path(package.source_url).as_uri(),
        },
    )

    cache_spy.assert_not_called()
    prepare_spy.assert_called_once()
    assert not prepare_spy.spy_return.exists(), "editable git should not be cached"
    assert not (prepare_spy.spy_return.parent / ".created_from_git_dependency").exists()


def test_executor_should_append_subdirectory_for_git(
    mocker: MockerFixture,
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    artifact_cache: ArtifactCache,
    io: BufferedIO,
    mock_file_downloads: None,
    wheel: Path,
) -> None:
    package = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_reference="master",
        source_resolved_reference="123456",
        source_url="https://github.com/demo/subdirectories.git",
        source_subdirectory="two",
    )

    chef = Chef(artifact_cache, tmp_venv, Factory.create_pool(config))
    chef.set_directory_wheel(wheel)
    spy = mocker.spy(chef, "prepare")

    executor = Executor(tmp_venv, pool, config, io)
    executor._chef = chef
    executor.execute([Install(package)])

    archive_arg = spy.call_args[0][0]
    assert archive_arg == tmp_venv.path / "src/demo/subdirectories/two"


def test_executor_should_write_pep610_url_references_for_git_with_subdirectories(
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    artifact_cache: ArtifactCache,
    io: BufferedIO,
    mock_file_downloads: None,
    wheel: Path,
) -> None:
    package = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_reference="master",
        source_resolved_reference="123456",
        source_url="https://github.com/demo/subdirectories.git",
        source_subdirectory="two",
    )

    chef = Chef(artifact_cache, tmp_venv, Factory.create_pool(config))
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
) -> None:
    config.merge({"installer": {"max-workers": max_workers}})

    mocker.patch("os.cpu_count", return_value=cpu_count, side_effect=side_effect)

    executor = Executor(tmp_venv, pool, config, io)

    assert executor._max_workers == expected_workers


def test_executor_fallback_on_poetry_create_error_without_wheel_installer(
    mocker: MockerFixture,
    config: Config,
    pool: RepositoryPool,
    io: BufferedIO,
    tmp_path: Path,
    mock_file_downloads: None,
    env: MockEnv,
    fixture_dir: FixtureDirGetter,
) -> None:
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
            "cache-dir": str(tmp_path),
            "installer": {"modern-installation": False},
        }
    )

    executor = Executor(env, pool, config, io)
    warning_lines = io.fetch_output().splitlines()
    assert warning_lines == [
        "Warning: Setting `installer.modern-installation` to `false` is deprecated.",
        "The pip-based installer will be removed in a future release.",
        "See https://github.com/python-poetry/poetry/issues/8987.",
    ]

    directory_package = Package(
        "simple-project",
        "1.2.3",
        source_type="directory",
        source_url=fixture_dir("simple_project").resolve().as_posix(),
    )

    return_code = executor.execute(
        [
            Install(directory_package),
        ]
    )

    expected = f"""
Package operations: 1 install, 0 updates, 0 removals

  - Installing simple-project (1.2.3 {directory_package.source_url})
"""

    expected_lines = set(expected.splitlines())
    output_lines = set(io.fetch_output().splitlines())
    assert output_lines == expected_lines
    assert return_code == 0
    assert mock_create_poetry.call_count == 1
    assert mock_sdist_builder.call_count == 0
    assert mock_editable_builder.call_count == 0
    assert mock_pip_install.call_count == 1
    assert mock_pip_install.call_args[1].get("upgrade") is True
    assert mock_pip_install.call_args[1].get("editable") is False


@pytest.mark.parametrize("failing_method", ["build", "get_requires_for_build"])
@pytest.mark.parametrize(
    "exception",
    [
        CalledProcessError(1, ["pip"], output=b"original error"),
        Exception("original error"),
    ],
)
@pytest.mark.parametrize("editable", [False, True])
def test_build_backend_errors_are_reported_correctly_if_caused_by_subprocess(
    failing_method: str,
    exception: Exception,
    editable: bool,
    mocker: MockerFixture,
    config: Config,
    pool: RepositoryPool,
    io: BufferedIO,
    mock_file_downloads: None,
    env: MockEnv,
    fixture_dir: FixtureDirGetter,
) -> None:
    error = BuildBackendException(exception, description="hide the original error")
    mocker.patch.object(ProjectBuilder, failing_method, side_effect=error)
    io.set_verbosity(Verbosity.NORMAL)

    executor = Executor(env, pool, config, io)

    package_name = "simple-project"
    package_version = "1.2.3"
    directory_package = Package(
        package_name,
        package_version,
        source_type="directory",
        source_url=fixture_dir("simple_project").resolve().as_posix(),
        develop=editable,
    )
    # must not be included in the error message
    directory_package.python_versions = ">=3.7"

    return_code = executor.execute([Install(directory_package)])

    assert return_code == 1

    package_url = directory_package.source_url
    expected_start = f"""
Package operations: 1 install, 0 updates, 0 removals

  - Installing {package_name} ({package_version} {package_url})

  ChefBuildError

  hide the original error
  \

  original error
"""

    assert directory_package.source_url is not None
    if editable:
        pip_command = "pip wheel --no-cache-dir --use-pep517 --editable"
        requirement = directory_package.source_url
        assert Path(requirement).exists()
    else:
        pip_command = "pip wheel --no-cache-dir --use-pep517"
        requirement = f"{package_name} @ {path_to_url(directory_package.source_url)}"
    expected_end = f"""
Note: This error originates from the build backend, and is likely not a problem with \
poetry but with {package_name} ({package_version} {package_url}) not supporting \
PEP 517 builds. You can verify this by running '{pip_command} "{requirement}"'.

"""

    output = io.fetch_output()
    assert output.startswith(expected_start)
    assert output.endswith(expected_end)


@pytest.mark.parametrize("encoding", ["utf-8", "latin-1"])
@pytest.mark.parametrize("stderr", [None, "Errör on stderr"])
def test_build_backend_errors_are_reported_correctly_if_caused_by_subprocess_encoding(
    encoding: str,
    stderr: str | None,
    mocker: MockerFixture,
    config: Config,
    pool: RepositoryPool,
    io: BufferedIO,
    mock_file_downloads: None,
    env: MockEnv,
    fixture_dir: FixtureDirGetter,
) -> None:
    """Test that the output of the subprocess is decoded correctly."""
    stdout = "Errör on stdout"
    error = BuildBackendException(
        CalledProcessError(
            1,
            ["pip"],
            output=stdout.encode(encoding),
            stderr=stderr.encode(encoding) if stderr else None,
        )
    )
    mocker.patch.object(ProjectBuilder, "get_requires_for_build", side_effect=error)
    io.set_verbosity(Verbosity.NORMAL)

    executor = Executor(env, pool, config, io)

    directory_package = Package(
        "simple-project",
        "1.2.3",
        source_type="directory",
        source_url=fixture_dir("simple_project").resolve().as_posix(),
    )

    return_code = executor.execute([Install(directory_package)])

    assert return_code == 1
    assert (stderr or stdout) in io.fetch_output()


def test_build_system_requires_not_available(
    config: Config,
    pool: RepositoryPool,
    io: BufferedIO,
    mock_file_downloads: None,
    env: MockEnv,
    fixture_dir: FixtureDirGetter,
) -> None:
    io.set_verbosity(Verbosity.NORMAL)

    executor = Executor(env, pool, config, io)

    package_name = "simple-project"
    package_version = "1.2.3"
    directory_package = Package(
        package_name,
        package_version,
        source_type="directory",
        source_url=fixture_dir("build_system_requires_not_available")
        .resolve()
        .as_posix(),
    )

    return_code = executor.execute([Install(directory_package)])

    assert return_code == 1

    package_url = directory_package.source_url
    expected_start = f"""\
Package operations: 1 install, 0 updates, 0 removals

  - Installing {package_name} ({package_version} {package_url})

  SolveFailure

  Because -root- depends on poetry-core (0.999) which doesn't match any versions,\
 version solving failed.
"""
    expected_end = "Cannot resolve build-system.requires for simple-project."

    output = io.fetch_output().strip()
    assert output.startswith(expected_start)
    assert output.endswith(expected_end)


def test_build_system_requires_install_failure(
    mocker: MockerFixture,
    config: Config,
    pool: RepositoryPool,
    io: BufferedIO,
    mock_file_downloads: None,
    env: MockEnv,
    fixture_dir: FixtureDirGetter,
) -> None:
    mocker.patch("poetry.installation.installer.Installer.run", return_value=1)
    mocker.patch("cleo.io.buffered_io.BufferedIO.fetch_output", return_value="output")
    mocker.patch("cleo.io.buffered_io.BufferedIO.fetch_error", return_value="error")
    io.set_verbosity(Verbosity.NORMAL)

    executor = Executor(env, pool, config, io)

    package_name = "simple-project"
    package_version = "1.2.3"
    directory_package = Package(
        package_name,
        package_version,
        source_type="directory",
        source_url=fixture_dir("simple_project").resolve().as_posix(),
    )

    return_code = executor.execute([Install(directory_package)])

    assert return_code == 1

    package_url = directory_package.source_url
    expected_start = f"""\
Package operations: 1 install, 0 updates, 0 removals

  - Installing {package_name} ({package_version} {package_url})

  ChefInstallError

  Failed to install poetry-core>=1.1.0a7.
  \

  Output:
  output
  \

  Error:
  error

"""
    expected_end = "Cannot install build-system.requires for simple-project."

    mocker.stopall()  # to get real output
    output = io.fetch_output().strip()
    assert output.startswith(expected_start)
    assert output.endswith(expected_end)


def test_other_error(
    config: Config,
    pool: RepositoryPool,
    io: BufferedIO,
    mock_file_downloads: None,
    env: MockEnv,
    fixture_dir: FixtureDirGetter,
) -> None:
    io.set_verbosity(Verbosity.NORMAL)

    executor = Executor(env, pool, config, io)

    package_name = "simple-project"
    package_version = "1.2.3"
    directory_package = Package(
        package_name,
        package_version,
        source_type="directory",
        source_url=fixture_dir("non-existing").resolve().as_posix(),
    )

    return_code = executor.execute([Install(directory_package)])

    assert return_code == 1

    package_url = directory_package.source_url
    expected_start = f"""\
Package operations: 1 install, 0 updates, 0 removals

  - Installing {package_name} ({package_version} {package_url})

  FileNotFoundError
"""
    expected_end = "Cannot install simple-project."

    output = io.fetch_output().strip()
    assert output.startswith(expected_start)
    assert output.endswith(expected_end)


@pytest.mark.parametrize(
    "package_files,expected_url_reference",
    [
        (
            [
                {
                    "file": "demo-0.1.0.tar.gz",
                    "hash": "sha512:766ecf369b6bdf801f6f7bbfe23923cc9793d633a55619472cd3d5763f9154711fbf57c8b6ca74e4a82fa9bd8380af831e7b8668e68e362669fc60b1d81d79ad",
                },
                {
                    "file": "demo-0.1.0.tar.gz",
                    "hash": "md5:d1912c917363a64e127318655f7d1fe7",
                },
                {
                    "file": "demo-0.1.0.whl",
                    "hash": "sha256:70e704135718fffbcbf61ed1fc45933cfd86951a744b681000eaaa75da31f17a",
                },
            ],
            {
                "archive_info": {
                    "hashes": {
                        "sha512": "766ecf369b6bdf801f6f7bbfe23923cc9793d633a55619472cd3d5763f9154711fbf57c8b6ca74e4a82fa9bd8380af831e7b8668e68e362669fc60b1d81d79ad"
                    },
                },
            },
        ),
        (
            [
                {
                    "file": "demo-0.1.0.tar.gz",
                    "hash": "md5:d1912c917363a64e127318655f7d1fe7",
                }
            ],
            {
                "archive_info": {
                    "hashes": {"md5": "d1912c917363a64e127318655f7d1fe7"},
                },
            },
        ),
        (
            [
                {
                    "file": "demo-0.1.0.tar.gz",
                    "hash": "sha3_512:196f4af9099185054ed72ca1d4c57707da5d724df0af7c3dfcc0fd018b0e0533908e790a291600c7d196fe4411b4f5f6db45213fe6e5cd5512bf18b2e9eff728",
                },
                {
                    "file": "demo-0.1.0.tar.gz",
                    "hash": "sha512:766ecf369b6bdf801f6f7bbfe23923cc9793d633a55619472cd3d5763f9154711fbf57c8b6ca74e4a82fa9bd8380af831e7b8668e68e362669fc60b1d81d79ad",
                },
                {
                    "file": "demo-0.1.0.tar.gz",
                    "hash": "md5:d1912c917363a64e127318655f7d1fe7",
                },
                {
                    "file": "demo-0.1.0.whl",
                    "hash": "sha256:70e704135718fffbcbf61ed1fc45933cfd86951a744b681000eaaa75da31f17a",
                },
            ],
            {
                "archive_info": {
                    "hashes": {
                        "sha3_512": "196f4af9099185054ed72ca1d4c57707da5d724df0af7c3dfcc0fd018b0e0533908e790a291600c7d196fe4411b4f5f6db45213fe6e5cd5512bf18b2e9eff728"
                    },
                },
            },
        ),
    ],
)
def test_executor_known_hashes(
    package_files: list[dict[str, str]],
    expected_url_reference: dict[str, Any],
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    io: BufferedIO,
    fixture_dir: FixtureDirGetter,
) -> None:
    package_source_url: Path = (
        fixture_dir("distributions") / "demo-0.1.0.tar.gz"
    ).resolve()
    package = Package(
        "demo", "0.1.0", source_type="file", source_url=package_source_url.as_posix()
    )
    package.files = package_files
    executor = Executor(tmp_venv, pool, config, io)
    executor.execute([Install(package)])
    expected_url_reference["url"] = package_source_url.as_uri()
    verify_installed_distribution(tmp_venv, package, expected_url_reference)


def test_executor_no_supported_hash_types(
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    io: BufferedIO,
    fixture_dir: FixtureDirGetter,
) -> None:
    url = (fixture_dir("distributions") / "demo-0.1.0.tar.gz").resolve()
    package = Package("demo", "0.1.0", source_type="file", source_url=url.as_posix())
    # Set package.files so the executor will attempt to hash the package
    package.files = [
        {
            "file": "demo-0.1.0.tar.gz",
            "hash": "hash_blah:1234567890abcdefghijklmnopqrstyzwxyz",
        },
        {
            "file": "demo-0.1.0.whl",
            "hash": "sha256:70e704135718fffbcbf61ed1fc45933cfd86951a744b681000eaaa75da31f17a",
        },
    ]

    executor = Executor(tmp_venv, pool, config, io)
    return_code = executor.execute([Install(package)])
    distributions = list(tmp_venv.site_packages.distributions(name=package.name))
    assert len(distributions) == 0

    output = io.fetch_output()
    error = io.fetch_error()
    assert return_code == 1, f"\noutput: {output}\nerror: {error}\n"
    assert "No usable hash type(s) for demo" in output
    assert "hash_blah:1234567890abcdefghijklmnopqrstyzwxyz" in output
