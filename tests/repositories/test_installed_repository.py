from __future__ import annotations

from collections import namedtuple
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils._compat import metadata
from poetry.utils.env import MockEnv as BaseMockEnv
from tests.compat import zipfile


if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture
    from poetry.core.packages.package import Package
    from pytest_mock.plugin import MockerFixture

FIXTURES_DIR = Path(__file__).parent / "fixtures"
ENV_DIR = (FIXTURES_DIR / "installed").resolve()
SITE_PURELIB = ENV_DIR / "lib" / "python3.7" / "site-packages"
SITE_PLATLIB = ENV_DIR / "lib64" / "python3.7" / "site-packages"
SRC = ENV_DIR / "src"
VENDOR_DIR = ENV_DIR / "vendor" / "py3.7"
INSTALLED_RESULTS = [
    metadata.PathDistribution(SITE_PURELIB / "cleo-0.7.6.dist-info"),
    metadata.PathDistribution(SRC / "pendulum" / "pendulum.egg-info"),
    metadata.PathDistribution(
        zipfile.Path(str(SITE_PURELIB / "foo-0.1.0-py3.8.egg"), "EGG-INFO")
    ),
    metadata.PathDistribution(VENDOR_DIR / "attrs-19.3.0.dist-info"),
    metadata.PathDistribution(SITE_PURELIB / "standard-1.2.3.dist-info"),
    metadata.PathDistribution(SITE_PURELIB / "editable-2.3.4.dist-info"),
    metadata.PathDistribution(SITE_PURELIB / "editable-with-import-2.3.4.dist-info"),
    metadata.PathDistribution(SITE_PLATLIB / "lib64-2.3.4.dist-info"),
    metadata.PathDistribution(SITE_PLATLIB / "bender-2.0.5.dist-info"),
    metadata.PathDistribution(SITE_PURELIB / "git_pep_610-1.2.3.dist-info"),
    metadata.PathDistribution(
        SITE_PURELIB / "git_pep_610_no_requested_version-1.2.3.dist-info"
    ),
    metadata.PathDistribution(
        SITE_PURELIB / "git_pep_610_subdirectory-1.2.3.dist-info"
    ),
    metadata.PathDistribution(SITE_PURELIB / "url_pep_610-1.2.3.dist-info"),
    metadata.PathDistribution(SITE_PURELIB / "file_pep_610-1.2.3.dist-info"),
    metadata.PathDistribution(SITE_PURELIB / "directory_pep_610-1.2.3.dist-info"),
    metadata.PathDistribution(
        SITE_PURELIB / "editable_directory_pep_610-1.2.3.dist-info"
    ),
]


class MockEnv(BaseMockEnv):
    @property
    def paths(self) -> dict[str, Path]:
        return {
            "purelib": SITE_PURELIB,
            "platlib": SITE_PLATLIB,
        }

    @property
    def sys_path(self) -> list[str]:
        return [str(path) for path in [ENV_DIR, SITE_PLATLIB, SITE_PURELIB]]


@pytest.fixture
def env() -> MockEnv:
    return MockEnv(path=ENV_DIR)


@pytest.fixture(autouse=True)
def mock_git_info(mocker: MockerFixture) -> None:
    mocker.patch(
        "poetry.vcs.git.Git.info",
        return_value=namedtuple("GitRepoLocalInfo", "origin revision")(
            origin="https://github.com/sdispater/pendulum.git",
            revision="bb058f6b78b2d28ef5d9a5e759cfa179a1a713d6",
        ),
    )


@pytest.fixture(autouse=True)
def mock_installed_repository_vendors(mocker: MockerFixture) -> None:
    mocker.patch("poetry.repositories.installed_repository._VENDORS", str(VENDOR_DIR))


@pytest.fixture
def repository(mocker: MockerFixture, env: MockEnv) -> InstalledRepository:
    mocker.patch(
        "poetry.utils._compat.metadata.Distribution.discover",
        return_value=INSTALLED_RESULTS,
    )
    return InstalledRepository.load(env)


def get_package_from_repository(
    name: str, repository: InstalledRepository
) -> Package | None:
    for pkg in repository.packages:
        if pkg.name == name:
            return pkg
    return None


def test_load_successful(repository: InstalledRepository):
    assert len(repository.packages) == len(INSTALLED_RESULTS) - 1


def test_load_successful_with_invalid_distribution(
    caplog: LogCaptureFixture, mocker: MockerFixture, env: MockEnv, tmp_dir: str
) -> None:
    invalid_dist_info = Path(tmp_dir) / "site-packages" / "invalid-0.1.0.dist-info"
    invalid_dist_info.mkdir(parents=True)
    mocker.patch(
        "poetry.utils._compat.metadata.Distribution.discover",
        return_value=INSTALLED_RESULTS + [metadata.PathDistribution(invalid_dist_info)],
    )
    repository_with_invalid_distribution = InstalledRepository.load(env)

    assert (
        len(repository_with_invalid_distribution.packages) == len(INSTALLED_RESULTS) - 1
    )
    assert len(caplog.messages) == 1

    message = caplog.messages[0]
    assert message.startswith("Project environment contains an invalid distribution")
    assert str(invalid_dist_info) in message


def test_load_ensure_isolation(repository: InstalledRepository):
    package = get_package_from_repository("attrs", repository)
    assert package is None


def test_load_standard_package(repository: InstalledRepository):
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


def test_load_git_package(repository: InstalledRepository):
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


def test_load_git_package_pth(repository: InstalledRepository):
    bender = get_package_from_repository("bender", repository)
    assert bender is not None
    assert bender.name == "bender"
    assert bender.version.text == "2.0.5"
    assert bender.source_type == "git"


def test_load_platlib_package(repository: InstalledRepository):
    lib64 = get_package_from_repository("lib64", repository)
    assert lib64 is not None
    assert lib64.name == "lib64"
    assert lib64.version.text == "2.3.4"


def test_load_editable_package(repository: InstalledRepository):
    # test editable package with text .pth file
    editable = get_package_from_repository("editable", repository)
    assert editable is not None
    assert editable.name == "editable"
    assert editable.version.text == "2.3.4"
    assert editable.source_type == "directory"
    assert (
        editable.source_url
        == Path("/path/to/editable").resolve(strict=False).as_posix()
    )


def test_load_editable_with_import_package(repository: InstalledRepository):
    # test editable package with executable .pth file
    editable = get_package_from_repository("editable-with-import", repository)
    assert editable is not None
    assert editable.name == "editable-with-import"
    assert editable.version.text == "2.3.4"
    assert editable.source_type is None
    assert editable.source_url is None


def test_load_standard_package_with_pth_file(repository: InstalledRepository):
    # test standard packages with .pth file is not treated as editable
    standard = get_package_from_repository("standard", repository)
    assert standard is not None
    assert standard.name == "standard"
    assert standard.version.text == "1.2.3"
    assert standard.source_type is None
    assert standard.source_url is None


def test_load_pep_610_compliant_git_packages(repository: InstalledRepository):
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
):
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
):
    package = get_package_from_repository("git-pep-610-subdirectory", repository)
    assert package is not None
    assert package.name == "git-pep-610-subdirectory"
    assert package.version.text == "1.2.3"
    assert package.source_type == "git"
    assert package.source_url == "https://github.com/demo/git-pep-610-subdirectory.git"
    assert package.source_reference == "my-branch"
    assert package.source_resolved_reference == "123456"
    assert package.source_subdirectory == "subdir"


def test_load_pep_610_compliant_url_packages(repository: InstalledRepository):
    package = get_package_from_repository("url-pep-610", repository)

    assert package is not None
    assert package.name == "url-pep-610"
    assert package.version.text == "1.2.3"
    assert package.source_type == "url"
    assert (
        package.source_url
        == "https://python-poetry.org/distributions/url-pep-610-1.2.3.tar.gz"
    )


def test_load_pep_610_compliant_file_packages(repository: InstalledRepository):
    package = get_package_from_repository("file-pep-610", repository)

    assert package is not None
    assert package.name == "file-pep-610"
    assert package.version.text == "1.2.3"
    assert package.source_type == "file"
    assert package.source_url == "/path/to/distributions/file-pep-610-1.2.3.tar.gz"


def test_load_pep_610_compliant_directory_packages(repository: InstalledRepository):
    package = get_package_from_repository("directory-pep-610", repository)

    assert package is not None
    assert package.name == "directory-pep-610"
    assert package.version.text == "1.2.3"
    assert package.source_type == "directory"
    assert package.source_url == "/path/to/distributions/directory-pep-610"
    assert not package.develop


def test_load_pep_610_compliant_editable_directory_packages(
    repository: InstalledRepository,
):
    package = get_package_from_repository("editable-directory-pep-610", repository)

    assert package is not None
    assert package.name == "editable-directory-pep-610"
    assert package.version.text == "1.2.3"
    assert package.source_type == "directory"
    assert package.source_url == "/path/to/distributions/directory-pep-610"
    assert package.develop
