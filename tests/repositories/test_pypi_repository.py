import json
import shutil

from io import BytesIO
from pathlib import Path

import pytest

from requests.exceptions import TooManyRedirects
from requests.models import Response

from poetry.core.packages.dependency import Dependency
from poetry.factory import Factory
from poetry.repositories.pypi_repository import PyPiRepository
from poetry.utils._compat import encode


class MockRepository(PyPiRepository):

    JSON_FIXTURES = Path(__file__).parent / "fixtures" / "pypi.org" / "json"
    DIST_FIXTURES = Path(__file__).parent / "fixtures" / "pypi.org" / "dists"

    def __init__(self, fallback=False):
        super(MockRepository, self).__init__(
            url="http://foo.bar", disable_cache=True, fallback=fallback
        )

    def _get(self, url):
        parts = url.split("/")[1:]
        name = parts[0]
        if len(parts) == 3:
            version = parts[1]
        else:
            version = None

        if not version:
            fixture = self.JSON_FIXTURES / (name + ".json")
        else:
            fixture = self.JSON_FIXTURES / name / (version + ".json")
            if not fixture.exists():
                fixture = self.JSON_FIXTURES / (name + ".json")

        if not fixture.exists():
            return

        with fixture.open(encoding="utf-8") as f:
            return json.loads(f.read())

    def _download(self, url, dest):
        filename = url.split("/")[-1]

        fixture = self.DIST_FIXTURES / filename

        shutil.copyfile(str(fixture), dest)


def test_find_packages():
    repo = MockRepository()
    packages = repo.find_packages(Factory.create_dependency("requests", "^2.18"))

    assert len(packages) == 5


def test_find_packages_with_prereleases():
    repo = MockRepository()
    packages = repo.find_packages(Factory.create_dependency("toga", ">=0.3.0.dev2"))

    assert len(packages) == 7


def test_find_packages_does_not_select_prereleases_if_not_allowed():
    repo = MockRepository()
    packages = repo.find_packages(Factory.create_dependency("pyyaml", "*"))

    assert len(packages) == 1


@pytest.mark.parametrize("constraint,count", [("*", 1), (">=1", 0), (">=19.0.0a0", 1)])
def test_find_packages_only_prereleases(constraint, count):
    repo = MockRepository()
    packages = repo.find_packages(Factory.create_dependency("black", constraint))

    assert len(packages) == count


def test_package():
    repo = MockRepository()

    package = repo.package("requests", "2.18.4")

    assert package.name == "requests"
    assert len(package.requires) == 9
    assert len([r for r in package.requires if r.is_optional()]) == 5
    assert len(package.extras["security"]) == 3
    assert len(package.extras["socks"]) == 2

    win_inet = package.extras["socks"][0]
    assert win_inet.name == "win-inet-pton"
    assert win_inet.python_versions == "~2.7 || ~2.6"
    assert str(win_inet.marker) == (
        'sys_platform == "win32" and (python_version == "2.7" '
        'or python_version == "2.6") and extra == "socks"'
    )


def test_fallback_on_downloading_packages():
    repo = MockRepository(fallback=True)

    package = repo.package("jupyter", "1.0.0")

    assert package.name == "jupyter"
    assert len(package.requires) == 6

    dependency_names = sorted([dep.name for dep in package.requires])
    assert dependency_names == [
        "ipykernel",
        "ipywidgets",
        "jupyter-console",
        "nbconvert",
        "notebook",
        "qtconsole",
    ]


def test_fallback_inspects_sdist_first_if_no_matching_wheels_can_be_found():
    repo = MockRepository(fallback=True)

    package = repo.package("isort", "4.3.4")

    assert package.name == "isort"
    assert len(package.requires) == 1

    dep = package.requires[0]
    assert dep.name == "futures"
    assert dep.python_versions == "~2.7"


def test_fallback_can_read_setup_to_get_dependencies():
    repo = MockRepository(fallback=True)

    package = repo.package("sqlalchemy", "1.2.12")

    assert package.name == "sqlalchemy"
    assert len(package.requires) == 9
    assert len([r for r in package.requires if r.is_optional()]) == 9

    assert package.extras == {
        "mssql_pymssql": [Dependency("pymssql", "*")],
        "mssql_pyodbc": [Dependency("pyodbc", "*")],
        "mysql": [Dependency("mysqlclient", "*")],
        "oracle": [Dependency("cx_oracle", "*")],
        "postgresql": [Dependency("psycopg2", "*")],
        "postgresql_pg8000": [Dependency("pg8000", "*")],
        "postgresql_psycopg2binary": [Dependency("psycopg2-binary", "*")],
        "postgresql_psycopg2cffi": [Dependency("psycopg2cffi", "*")],
        "pymysql": [Dependency("pymysql", "*")],
    }


def test_pypi_repository_supports_reading_bz2_files():
    repo = MockRepository(fallback=True)

    package = repo.package("twisted", "18.9.0")

    assert package.name == "twisted"
    assert 71 == len(package.requires)
    assert sorted(
        [r for r in package.requires if not r.is_optional()], key=lambda r: r.name
    ) == [
        Dependency("attrs", ">=17.4.0"),
        Dependency("Automat", ">=0.3.0"),
        Dependency("constantly", ">=15.1"),
        Dependency("hyperlink", ">=17.1.1"),
        Dependency("incremental", ">=16.10.1"),
        Dependency("PyHamcrest", ">=1.9.0"),
        Dependency("zope.interface", ">=4.4.2"),
    ]

    expected_extras = {
        "all_non_platform": [
            Dependency("appdirs", ">=1.4.0"),
            Dependency("cryptography", ">=1.5"),
            Dependency("h2", ">=3.0,<4.0"),
            Dependency("idna", ">=0.6,!=2.3"),
            Dependency("priority", ">=1.1.0,<2.0"),
            Dependency("pyasn1", "*"),
            Dependency("pyopenssl", ">=16.0.0"),
            Dependency("pyserial", ">=3.0"),
            Dependency("service_identity", "*"),
            Dependency("soappy", "*"),
        ]
    }

    for name, deps in expected_extras.items():
        assert expected_extras[name] == sorted(
            package.extras[name], key=lambda r: r.name
        )


def test_invalid_versions_ignored():
    repo = MockRepository()

    # the json metadata for this package contains one malformed version
    # and a correct one.
    packages = repo.find_packages(Factory.create_dependency("pygame-music-grid", "*"))
    assert len(packages) == 1


def test_get_should_invalid_cache_on_too_many_redirects_error(mocker):
    delete_cache = mocker.patch("cachecontrol.caches.file_cache.FileCache.delete")

    response = Response()
    response.encoding = "utf-8"
    response.raw = BytesIO(encode('{"foo": "bar"}'))
    mocker.patch(
        "cachecontrol.adapter.CacheControlAdapter.send",
        side_effect=[TooManyRedirects(), response],
    )
    repository = PyPiRepository()
    repository._get("https://pypi.org/pypi/async-timeout/json")

    assert delete_cache.called


def test_urls():
    repository = PyPiRepository()

    assert "https://pypi.org/simple/" == repository.url
    assert "https://pypi.org/simple/" == repository.authenticated_url


def test_use_pypi_pretty_name():
    repo = MockRepository(fallback=True)

    package = repo.find_packages(Factory.create_dependency("twisted", "*"))
    assert len(package) == 1
    assert package[0].pretty_name == "Twisted"
