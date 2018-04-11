from poetry.packages import Dependency
from poetry.packages import Package

from poetry.semver.helpers import normalize_version
from poetry.utils._compat import Path


FIXTURE_PATH = Path(__file__).parent / 'fixtures'


def get_package(name, version):
    return Package(name, normalize_version(version), version)


def get_dependency(name,
                   constraint=None,
                   category='main',
                   optional=False,
                   allows_prereleases=False):
    return Dependency(
        name,
        constraint or '*',
        category=category,
        optional=optional,
        allows_prereleases=allows_prereleases
    )


def fixture(path=None):
    if path:
        return FIXTURE_PATH / path
    else:
        return FIXTURE_PATH
