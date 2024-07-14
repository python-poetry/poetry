from __future__ import annotations

import os
import shutil
import zipfile

from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Iterator
from typing import NamedTuple

import pytest

from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils._compat import getencoding
from poetry.utils._compat import metadata
from poetry.utils.env import EnvManager
from poetry.utils.env import MockEnv
from poetry.utils.env import VirtualEnv
from tests.helpers import with_working_directory


if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture
    from poetry.core.packages.package import Package
    from pytest_mock.plugin import MockerFixture

    from poetry.poetry import Poetry
    from tests.types import FixtureDirGetter
    from tests.types import ProjectFactory


@pytest.fixture(scope="session")
def env_dir(tmp_session_working_directory: Path) -> Iterator[Path]:
    source = Path(__file__).parent / "fixtures" / "installed"
    target = tmp_session_working_directory / source.name

    with with_working_directory(source=source, target=target) as path:
        yield path


@pytest.fixture(scope="session")
def site_purelib(env_dir: Path) -> Path:
    return env_dir / "lib" / "python3.7" / "site-packages"


@pytest.fixture(scope="session")
def site_platlib(env_dir: Path) -> Path:
    return env_dir / "lib64" / "python3.7" / "site-packages"


@pytest.fixture(scope="session")
def src_dir(env_dir: Path) -> Path:
    return env_dir / "src"


@pytest.fixture(scope="session")
def installed_results(
    site_purelib: Path, site_platlib: Path, src_dir: Path
) -> list[metadata.PathDistribution]:
    return [
        metadata.PathDistribution(site_purelib / "cleo-0.7.6.dist-info"),
        metadata.PathDistribution(src_dir / "pendulum" / "pendulum.egg-info"),
        metadata.PathDistribution(
            zipfile.Path(  # type: ignore[arg-type]
                site_purelib / "foo-0.1.0-py3.8.egg",
                "EGG-INFO",
            )
        ),
        metadata.PathDistribution(site_purelib / "standard-1.2.3.dist-info"),
        metadata.PathDistribution(site_purelib / "editable-2.3.4.dist-info"),
        metadata.PathDistribution(site_purelib / "editable-src-dir-2.3.4.dist-info"),
        metadata.PathDistribution(
            site_purelib / "editable-with-import-2.3.4.dist-info"
        ),
        metadata.PathDistribution(site_platlib / "lib64-2.3.4.dist-info"),
        metadata.PathDistribution(site_platlib / "bender-2.0.5.dist-info"),
        metadata.PathDistribution(site_purelib / "git_pep_610-1.2.3.dist-info"),
        metadata.PathDistribution(
            site_purelib / "git_pep_610_no_requested_version-1.2.3.dist-info"
        ),
        metadata.PathDistribution(
            site_purelib / "git_pep_610_subdirectory-1.2.3.dist-info"
        ),
        metadata.PathDistribution(site_purelib / "url_pep_610-1.2.3.dist-info"),
        metadata.PathDistribution(site_purelib / "file_pep_610-1.2.3.dist-info"),
        metadata.PathDistribution(site_purelib / "directory_pep_610-1.2.3.dist-info"),
        metadata.PathDistribution(
            site_purelib / "editable_directory_pep_610-1.2.3.dist-info"
        ),
    ]


@pytest.fixture
def env(
    env_dir: Path, site_purelib: Path, site_platlib: Path, src_dir: Path
) -> MockEnv:
    class _MockEnv(MockEnv):
        @cached_property
        def paths(self) -> dict[str, str]:
            return {
                "purelib": site_purelib.as_posix(),
                "platlib": site_platlib.as_posix(),
            }

        @property
        def sys_path(self) -> list[str]:
            return [str(path) for path in [env_dir, site_platlib, site_purelib]]

    return _MockEnv(path=env_dir)


@pytest.fixture(autouse=True)
def mock_git_info(mocker: MockerFixture) -> None:
    class GitRepoLocalInfo(NamedTuple):
        origin: str
        revision: str

    mocker.patch(
        "poetry.vcs.git.Git.info",
        return_value=GitRepoLocalInfo(
            origin="https://github.com/sdispater/pendulum.git",
            revision="bb058f6b78b2d28ef5d9a5e759cfa179a1a713d6",
        ),
    )


@pytest.fixture
def repository(
    mocker: MockerFixture,
    env: MockEnv,
    installed_results: list[metadata.PathDistribution],
) -> InstalledRepository:
    mocker.patch(
        "poetry.utils._compat.metadata.Distribution.discover",
        return_value=installed_results,
    )
    return InstalledRepository.load(env)


def get_package_from_repository(
    name: str, repository: InstalledRepository
) -> Package | None:
    for pkg in repository.packages:
        if pkg.name == name:
            return pkg
    return None


@pytest.fixture
def poetry(
    project_factory: ProjectFactory,
    fixture_dir: FixtureDirGetter,
    installed_results: list[metadata.PathDistribution],
) -> Poetry:
    return project_factory("simple", source=fixture_dir("simple_project"))


@pytest.fixture(scope="session")
def editable_source_directory_path() -> str:
    return Path("/path/to/editable").resolve(strict=False).as_posix()


@pytest.fixture(scope="session", autouse=(os.name == "nt"))
def fix_editable_path_for_windows(
    site_purelib: Path, editable_source_directory_path: str
) -> None:
    # we handle this as a special case since in certain scenarios (eg: on Windows GHA runners)
    # the temp directory is on a different drive causing path resolutions without drive letters
    # to give inconsistent results at different phases of the test suite execution; additionally
    # this represents a more realistic scenario
    editable_pth_file = site_purelib / "editable.pth"
    editable_pth_file.write_text(editable_source_directory_path, encoding=getencoding())


def test_load_successful(
    repository: InstalledRepository, installed_results: list[metadata.PathDistribution]
) -> None:
    assert len(repository.packages) == len(installed_results)


def test_load_successful_with_invalid_distribution(
    caplog: LogCaptureFixture,
    mocker: MockerFixture,
    env: MockEnv,
    tmp_path: Path,
    installed_results: list[metadata.PathDistribution],
) -> None:
    invalid_dist_info = tmp_path / "site-packages" / "invalid-0.1.0.dist-info"
    invalid_dist_info.mkdir(parents=True)
    mocker.patch(
        "poetry.utils._compat.metadata.Distribution.discover",
        return_value=[*installed_results, metadata.PathDistribution(invalid_dist_info)],
    )
    repository_with_invalid_distribution = InstalledRepository.load(env)

    assert len(repository_with_invalid_distribution.packages) == len(installed_results)
    assert len(caplog.messages) == 1

    message = caplog.messages[0]
    assert message.startswith("Project environment contains an invalid distribution")
    assert str(invalid_dist_info) in message


def test_loads_in_correct_sys_path_order(
    tmp_path: Path, current_python: tuple[int, int, int], fixture_dir: FixtureDirGetter
) -> None:
    path1 = tmp_path / "path1"
    path1.mkdir()
    path2 = tmp_path / "path2"
    path2.mkdir()
    env = MockEnv(path=tmp_path, sys_path=[str(path1), str(path2)])
    fixtures = fixture_dir("project_plugins")
    dist_info_1 = "my_application_plugin-1.0.dist-info"
    dist_info_2 = "my_application_plugin-2.0.dist-info"
    dist_info_other = "my_other_plugin-1.0.dist-info"
    shutil.copytree(fixtures / dist_info_1, path1 / dist_info_1)
    shutil.copytree(fixtures / dist_info_2, path2 / dist_info_2)
    shutil.copytree(fixtures / dist_info_other, path2 / dist_info_other)

    repo = InstalledRepository.load(env)

    assert {f"{p.name} {p.version}" for p in repo.packages} == {
        "my-application-plugin 1.0",
        "my-other-plugin 1.0",
    }


def test_load_ensure_isolation(repository: InstalledRepository) -> None:
    package = get_package_from_repository("attrs", repository)
    assert package is None


def test_load_standard_package(repository: InstalledRepository) -> None:
    cleo = get_package_from_repository("cleo", repository)
    assert cleo is not None
    assert cleo.name == "cleo"
    assert cleo.version.text == "0.7.6"
    assert (
        cleo.description
        == "Cleo allows you to create beautiful and testable command-line interfaces."
    )

    foo = get_package_from_repository("foo", repository)
    assert foo is not None
    assert foo.version.text == "0.1.0"


def test_load_git_package(repository: InstalledRepository) -> None:
    pendulum = get_package_from_repository("pendulum", repository)
    assert pendulum is not None
    assert pendulum.name == "pendulum"
    assert pendulum.version.text == "2.0.5"
    assert pendulum.description == "Python datetimes made easy"
    assert pendulum.source_type == "git"
    assert pendulum.source_url in [
        "git@github.com:sdispater/pendulum.git",
        "https://github.com/sdispater/pendulum.git",
    ]
    assert pendulum.source_reference == "bb058f6b78b2d28ef5d9a5e759cfa179a1a713d6"


def test_load_git_package_pth(repository: InstalledRepository) -> None:
    bender = get_package_from_repository("bender", repository)
    assert bender is not None
    assert bender.name == "bender"
    assert bender.version.text == "2.0.5"
    assert bender.source_type == "git"


def test_load_platlib_package(repository: InstalledRepository) -> None:
    lib64 = get_package_from_repository("lib64", repository)
    assert lib64 is not None
    assert lib64.name == "lib64"
    assert lib64.version.text == "2.3.4"


def test_load_editable_package(
    repository: InstalledRepository, editable_source_directory_path: str
) -> None:
    # test editable package with text .pth file
    editable = get_package_from_repository("editable", repository)
    assert editable is not None
    assert editable.name == "editable"
    assert editable.version.text == "2.3.4"
    assert editable.source_type == "directory"
    assert editable.source_url == editable_source_directory_path


def test_load_editable_src_dir_package(
    repository: InstalledRepository, editable_source_directory_path: str
) -> None:
    # test editable package with src layout with text .pth file
    editable = get_package_from_repository("editable-src-dir", repository)
    assert editable is not None
    assert editable.name == "editable-src-dir"
    assert editable.version.text == "2.3.4"
    assert editable.source_type == "directory"
    assert editable.source_url == editable_source_directory_path


def test_load_editable_with_import_package(repository: InstalledRepository) -> None:
    # test editable package with executable .pth file
    editable = get_package_from_repository("editable-with-import", repository)
    assert editable is not None
    assert editable.name == "editable-with-import"
    assert editable.version.text == "2.3.4"
    assert editable.source_type is None
    assert editable.source_url is None


def test_load_standard_package_with_pth_file(repository: InstalledRepository) -> None:
    # test standard packages with .pth file is not treated as editable
    standard = get_package_from_repository("standard", repository)
    assert standard is not None
    assert standard.name == "standard"
    assert standard.version.text == "1.2.3"
    assert standard.source_type is None
    assert standard.source_url is None


def test_load_pep_610_compliant_git_packages(repository: InstalledRepository) -> None:
    package = get_package_from_repository("git-pep-610", repository)

    assert package is not None
    assert package.name == "git-pep-610"
    assert package.version.text == "1.2.3"
    assert package.source_type == "git"
    assert package.source_url == "https://github.com/demo/git-pep-610.git"
    assert package.source_reference == "my-branch"
    assert package.source_resolved_reference == "123456"


def test_load_pep_610_compliant_git_packages_no_requested_version(
    repository: InstalledRepository,
) -> None:
    package = get_package_from_repository(
        "git-pep-610-no-requested-version", repository
    )

    assert package is not None
    assert package.name == "git-pep-610-no-requested-version"
    assert package.version.text == "1.2.3"
    assert package.source_type == "git"
    assert (
        package.source_url
        == "https://github.com/demo/git-pep-610-no-requested-version.git"
    )
    assert package.source_resolved_reference == "123456"
    assert package.source_reference == package.source_resolved_reference


def test_load_pep_610_compliant_git_packages_with_subdirectory(
    repository: InstalledRepository,
) -> None:
    package = get_package_from_repository("git-pep-610-subdirectory", repository)
    assert package is not None
    assert package.name == "git-pep-610-subdirectory"
    assert package.version.text == "1.2.3"
    assert package.source_type == "git"
    assert package.source_url == "https://github.com/demo/git-pep-610-subdirectory.git"
    assert package.source_reference == "my-branch"
    assert package.source_resolved_reference == "123456"
    assert package.source_subdirectory == "subdir"


def test_load_pep_610_compliant_url_packages(repository: InstalledRepository) -> None:
    package = get_package_from_repository("url-pep-610", repository)

    assert package is not None
    assert package.name == "url-pep-610"
    assert package.version.text == "1.2.3"
    assert package.source_type == "url"
    assert (
        package.source_url
        == "https://mock.pythonhosted.org/distributions/url-pep-610-1.2.3.tar.gz"
    )


def test_load_pep_610_compliant_file_packages(repository: InstalledRepository) -> None:
    package = get_package_from_repository("file-pep-610", repository)

    assert package is not None
    assert package.name == "file-pep-610"
    assert package.version.text == "1.2.3"
    assert package.source_type == "file"
    assert package.source_url == "/path/to/distributions/file-pep-610-1.2.3.tar.gz"


def test_load_pep_610_compliant_directory_packages(
    repository: InstalledRepository,
) -> None:
    package = get_package_from_repository("directory-pep-610", repository)

    assert package is not None
    assert package.name == "directory-pep-610"
    assert package.version.text == "1.2.3"
    assert package.source_type == "directory"
    assert package.source_url == "/path/to/distributions/directory-pep-610"
    assert not package.develop


def test_load_pep_610_compliant_editable_directory_packages(
    repository: InstalledRepository,
) -> None:
    package = get_package_from_repository("editable-directory-pep-610", repository)

    assert package is not None
    assert package.name == "editable-directory-pep-610"
    assert package.version.text == "1.2.3"
    assert package.source_type == "directory"
    assert package.source_url == "/path/to/distributions/directory-pep-610"
    assert package.develop


def test_system_site_packages_source_type(
    tmp_path: Path, mocker: MockerFixture, poetry: Poetry, site_purelib: Path
) -> None:
    """
    The source type of system site packages
    must not be falsely identified as "directory".
    """
    venv_path = tmp_path / "venv"
    site_path = tmp_path / "site"
    for dist_info in {"cleo-0.7.6.dist-info", "directory_pep_610-1.2.3.dist-info"}:
        shutil.copytree(site_purelib / dist_info, site_path / dist_info)
    mocker.patch("poetry.utils.env.virtual_env.VirtualEnv.sys_path", [str(site_path)])
    mocker.patch("site.getsitepackages", return_value=[str(site_path)])

    EnvManager(poetry).build_venv(path=venv_path, flags={"system-site-packages": True})
    env = VirtualEnv(venv_path)
    installed_repository = InstalledRepository.load(env)

    source_types = {
        package.name: package.source_type for package in installed_repository.packages
    }
    assert source_types == {"cleo": None, "directory-pep-610": "directory"}


def test_pipx_shared_lib_site_packages(
    tmp_path: Path,
    poetry: Poetry,
    site_purelib: Path,
    caplog: LogCaptureFixture,
) -> None:
    """
    Simulate pipx shared/lib/site-packages which is not relative to the venv path.
    """
    venv_path = tmp_path / "venv"
    shared_lib_site_path = tmp_path / "site"
    env = MockEnv(
        path=venv_path, sys_path=[str(venv_path / "purelib"), str(shared_lib_site_path)]
    )
    dist_info = "cleo-0.7.6.dist-info"
    shutil.copytree(site_purelib / dist_info, shared_lib_site_path / dist_info)
    installed_repository = InstalledRepository.load(env)

    assert len(installed_repository.packages) == 1
    cleo_package = installed_repository.packages[0]
    cleo_package.to_dependency()
    # There must not be a warning
    # that the package does not seem to be a valid Python package.
    assert caplog.messages == []
    assert cleo_package.source_type is None
