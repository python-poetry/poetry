import pytest

from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils._compat import PY36
from poetry.utils._compat import Path
from poetry.utils._compat import metadata
from poetry.utils._compat import zipp
from poetry.utils.env import MockEnv as BaseMockEnv
from pytest_mock.plugin import MockFixture


FIXTURES_DIR = Path(__file__).parent / "fixtures"
ENV_DIR = (FIXTURES_DIR / "installed").resolve()
SITE_PACKAGES = ENV_DIR / "lib" / "python3.7" / "site-packages"
SRC = ENV_DIR / "src"
VENDOR_DIR = ENV_DIR / "vendor" / "py3.7"
INSTALLED_RESULTS = [
    metadata.PathDistribution(SITE_PACKAGES / "cleo-0.7.6.dist-info"),
    metadata.PathDistribution(SRC / "pendulum" / "pendulum.egg-info"),
    metadata.PathDistribution(
        zipp.Path(str(SITE_PACKAGES / "foo-0.1.0-py3.8.egg"), "EGG-INFO")
    ),
    metadata.PathDistribution(VENDOR_DIR / "attrs-19.3.0.dist-info"),
    metadata.PathDistribution(SITE_PACKAGES / "editable-2.3.4.dist-info"),
    metadata.PathDistribution(SITE_PACKAGES / "editable-with-import-2.3.4.dist-info"),
]


class MockEnv(BaseMockEnv):
    @property
    def site_packages(self):  # type: () -> Path
        return SITE_PACKAGES


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


def test_load_successful(repository):
    assert len(repository.packages) == 5


def test_load_ensure_isolation(repository):
    for pkg in repository.packages:
        assert pkg.name != "attrs"


def test_load_standard_package(repository):
    cleo = repository.packages[0]
    assert cleo.name == "cleo"
    assert cleo.version.text == "0.7.6"
    assert (
        cleo.description
        == "Cleo allows you to create beautiful and testable command-line interfaces."
    )

    foo = repository.packages[3]
    assert foo.name == "foo"
    assert foo.version.text == "0.1.0"


def test_load_git_package(repository):
    pendulum = repository.packages[4]
    assert pendulum.name == "pendulum"
    assert pendulum.version.text == "2.0.5"
    assert pendulum.description == "Python datetimes made easy"
    assert pendulum.source_type == "git"
    assert pendulum.source_url == "https://github.com/sdispater/pendulum.git"
    assert pendulum.source_reference == "bb058f6b78b2d28ef5d9a5e759cfa179a1a713d6"


@pytest.mark.skipif(
    not PY36, reason="pathlib.resolve() does not support strict argument"
)
def test_load_editable_package(repository):
    # test editable package with text .pth file
    editable = repository.packages[1]
    assert editable.name == "editable"
    assert editable.version.text == "2.3.4"
    assert editable.source_type == "directory"
    assert (
        editable.source_url
        == Path("/path/to/editable").resolve(strict=False).as_posix()
    )


def test_load_editable_with_import_package(repository):
    # test editable package with executable .pth file
    editable = repository.packages[2]
    assert editable.name == "editable-with-import"
    assert editable.version.text == "2.3.4"
    assert editable.source_type == ""
    assert editable.source_url == ""
