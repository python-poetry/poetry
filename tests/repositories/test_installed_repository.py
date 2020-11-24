from pathlib import Path
from typing import Optional

import pytest

from pytest_mock.plugin import MockFixture

from poetry.core.packages import Package
from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils._compat import metadata
from poetry.utils.env import MockEnv as BaseMockEnv
from tests.compat import zipp


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
        zipp.Path(str(SITE_PURELIB / "foo-0.1.0-py3.8.egg"), "EGG-INFO")
    ),
    metadata.PathDistribution(VENDOR_DIR / "attrs-19.3.0.dist-info"),
    metadata.PathDistribution(SITE_PURELIB / "standard-1.2.3.dist-info"),
    metadata.PathDistribution(SITE_PURELIB / "editable-2.3.4.dist-info"),
    metadata.PathDistribution(SITE_PURELIB / "editable-with-import-2.3.4.dist-info"),
    metadata.PathDistribution(SITE_PLATLIB / "lib64-2.3.4.dist-info"),
    metadata.PathDistribution(SITE_PLATLIB / "bender-2.0.5.dist-info"),
]


class MockEnv(BaseMockEnv):
    @property
    def paths(self):
        return {
            "purelib": SITE_PURELIB,
            "platlib": SITE_PLATLIB,
        }

    @property
    def sys_path(self):
        return [ENV_DIR, SITE_PLATLIB, SITE_PURELIB]


@pytest.fixture
def env():  # type: () -> MockEnv
    return MockEnv(path=ENV_DIR)


@pytest.fixture
def repository(mocker, env):  # type: (MockFixture, MockEnv) -> InstalledRepository
    mocker.patch(
        "poetry.utils._compat.metadata.Distribution.discover",
        return_value=INSTALLED_RESULTS,
    )
    mocker.patch(
        "poetry.core.vcs.git.Git.rev_parse",
        return_value="bb058f6b78b2d28ef5d9a5e759cfa179a1a713d6",
    )
    mocker.patch(
        "poetry.core.vcs.git.Git.remote_urls",
        side_effect=[
            {"remote.origin.url": "https://github.com/sdispater/pendulum.git"},
            {"remote.origin.url": "git@github.com:sdispater/pendulum.git"},
        ],
    )
    mocker.patch("poetry.repositories.installed_repository._VENDORS", str(VENDOR_DIR))
    return InstalledRepository.load(env)


def get_package_from_repository(
    name, repository
):  # type: (str, InstalledRepository) -> Optional[Package]
    for pkg in repository.packages:
        if pkg.name == name:
            return pkg
    return None


def test_load_successful(repository):
    assert len(repository.packages) == len(INSTALLED_RESULTS) - 1


def test_load_ensure_isolation(repository):
    package = get_package_from_repository("attrs", repository)
    assert package is None


def test_load_standard_package(repository):
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


def test_load_git_package(repository):
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


def test_load_git_package_pth(repository):
    bender = get_package_from_repository("bender", repository)
    assert bender is not None
    assert bender.name == "bender"
    assert bender.version.text == "2.0.5"
    assert bender.source_type == "git"


def test_load_platlib_package(repository):
    lib64 = get_package_from_repository("lib64", repository)
    assert lib64 is not None
    assert lib64.name == "lib64"
    assert lib64.version.text == "2.3.4"


def test_load_editable_package(repository):
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


def test_load_editable_with_import_package(repository):
    # test editable package with executable .pth file
    editable = get_package_from_repository("editable-with-import", repository)
    assert editable is not None
    assert editable.name == "editable-with-import"
    assert editable.version.text == "2.3.4"
    assert editable.source_type is None
    assert editable.source_url is None


def test_load_standard_package_with_pth_file(repository):
    # test standard packages with .pth file is not treated as editable
    standard = get_package_from_repository("standard", repository)
    assert standard is not None
    assert standard.name == "standard"
    assert standard.version.text == "1.2.3"
    assert standard.source_type is None
    assert standard.source_url is None
