from __future__ import annotations

import json
import shutil

from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest

from poetry.core.constraints.version import Version
from poetry.core.packages.dependency import Dependency
from requests.exceptions import TooManyRedirects
from requests.models import Response

from poetry.factory import Factory
from poetry.repositories.pypi_repository import PyPiRepository
from poetry.utils._compat import encode


if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(autouse=True)
def _use_simple_keyring(with_simple_keyring: None) -> None:
    pass


class MockRepository(PyPiRepository):
    JSON_FIXTURES = Path(__file__).parent / "fixtures" / "pypi.org" / "json"
    DIST_FIXTURES = Path(__file__).parent / "fixtures" / "pypi.org" / "dists"

    def __init__(self, fallback: bool = False) -> None:
        super().__init__(url="http://foo.bar", disable_cache=True, fallback=fallback)

    def _get(
        self, url: str, headers: dict[str, str] | None = None
    ) -> dict[str, Any] | None:
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
            return None

        with fixture.open(encoding="utf-8") as f:
            return json.loads(f.read())

    def _download(self, url: str, dest: Path) -> None:
        filename = url.split("/")[-1]

        fixture = self.DIST_FIXTURES / filename

        shutil.copyfile(str(fixture), dest)


def test_find_packages() -> None:
    repo = MockRepository()
    packages = repo.find_packages(Factory.create_dependency("requests", "^2.18"))

    assert len(packages) == 5


def test_find_packages_with_prereleases() -> None:
    repo = MockRepository()
    packages = repo.find_packages(Factory.create_dependency("toga", ">=0.3.0.dev2"))

    assert len(packages) == 7


def test_find_packages_does_not_select_prereleases_if_not_allowed() -> None:
    repo = MockRepository()
    packages = repo.find_packages(Factory.create_dependency("pyyaml", "*"))

    assert len(packages) == 1


@pytest.mark.parametrize(
    ["constraint", "count"], [("*", 1), (">=1", 0), (">=19.0.0a0", 1)]
)
def test_find_packages_only_prereleases(constraint: str, count: int) -> None:
    repo = MockRepository()
    packages = repo.find_packages(Factory.create_dependency("black", constraint))

    assert len(packages) == count


@pytest.mark.parametrize(
    ["constraint", "expected"],
    [
        # yanked 21.11b0 is ignored except for pinned version
        ("*", ["19.10b0"]),
        (">=19.0a0", ["19.10b0"]),
        (">=20.0a0", []),
        (">=21.11b0", []),
        ("==21.11b0", ["21.11b0"]),
    ],
)
def test_find_packages_yanked(constraint: str, expected: list[str]) -> None:
    repo = MockRepository()
    packages = repo.find_packages(Factory.create_dependency("black", constraint))

    assert [str(p.version) for p in packages] == expected


def test_package() -> None:
    repo = MockRepository()

    package = repo.package("requests", Version.parse("2.18.4"))

    assert package.name == "requests"
    assert len(package.requires) == 9
    assert len([r for r in package.requires if r.is_optional()]) == 5
    assert len(package.extras["security"]) == 3
    assert len(package.extras["socks"]) == 2

    assert package.files == [
        {
            "file": "requests-2.18.4-py2.py3-none-any.whl",
            "hash": "sha256:6a1b267aa90cac58ac3a765d067950e7dbbf75b1da07e895d1f594193a40a38b",  # noqa: E501
        },
        {
            "file": "requests-2.18.4.tar.gz",
            "hash": "sha256:9c443e7324ba5b85070c4a818ade28bfabedf16ea10206da1132edaa6dda237e",  # noqa: E501
        },
    ]

    win_inet = package.extras["socks"][0]
    assert win_inet.name == "win-inet-pton"
    assert win_inet.python_versions == "~2.7 || ~2.6"

    # Different versions of poetry-core simplify the following marker differently,
    # either is fine.
    marker1 = (
        'sys_platform == "win32" and (python_version == "2.7" or python_version =='
        ' "2.6") and extra == "socks"'
    )
    marker2 = (
        'sys_platform == "win32" and python_version == "2.7" and extra == "socks" or'
        ' sys_platform == "win32" and python_version == "2.6" and extra == "socks"'
    )
    assert str(win_inet.marker) in {marker1, marker2}


@pytest.mark.parametrize(
    "package_name, version, yanked, yanked_reason",
    [
        ("black", "19.10b0", False, ""),
        ("black", "21.11b0", True, "Broken regex dependency. Use 21.11b1 instead."),
    ],
)
def test_package_yanked(
    package_name: str, version: str, yanked: bool, yanked_reason: str
) -> None:
    repo = MockRepository()

    package = repo.package(package_name, Version.parse(version))

    assert package.name == package_name
    assert str(package.version) == version
    assert package.yanked is yanked
    assert package.yanked_reason == yanked_reason


def test_package_not_canonicalized() -> None:
    repo = MockRepository()

    package = repo.package("discord.py", Version.parse("2.0.0"))

    assert package.name == "discord-py"
    assert package.pretty_name == "discord.py"


@pytest.mark.parametrize(
    "package_name, version, yanked, yanked_reason",
    [
        ("black", "19.10b0", False, ""),
        ("black", "21.11b0", True, "Broken regex dependency. Use 21.11b1 instead."),
    ],
)
def test_find_links_for_package_yanked(
    package_name: str, version: str, yanked: bool, yanked_reason: str
) -> None:
    repo = MockRepository()

    package = repo.package(package_name, Version.parse(version))
    links = repo.find_links_for_package(package)

    assert len(links) == 2
    for link in links:
        assert link.yanked == yanked
        assert link.yanked_reason == yanked_reason


def test_fallback_on_downloading_packages() -> None:
    repo = MockRepository(fallback=True)

    package = repo.package("jupyter", Version.parse("1.0.0"))

    assert package.name == "jupyter"
    assert len(package.requires) == 6

    dependency_names = sorted(dep.name for dep in package.requires)
    assert dependency_names == [
        "ipykernel",
        "ipywidgets",
        "jupyter-console",
        "nbconvert",
        "notebook",
        "qtconsole",
    ]


def test_fallback_inspects_sdist_first_if_no_matching_wheels_can_be_found() -> None:
    repo = MockRepository(fallback=True)

    package = repo.package("isort", Version.parse("4.3.4"))

    assert package.name == "isort"
    assert len(package.requires) == 1

    dep = package.requires[0]
    assert dep.name == "futures"
    assert dep.python_versions == "~2.7"


def test_fallback_can_read_setup_to_get_dependencies() -> None:
    repo = MockRepository(fallback=True)

    package = repo.package("sqlalchemy", Version.parse("1.2.12"))

    assert package.name == "sqlalchemy"
    assert len(package.requires) == 9
    assert len([r for r in package.requires if r.is_optional()]) == 9

    assert package.extras == {
        "mssql-pymssql": [Dependency("pymssql", "*")],
        "mssql-pyodbc": [Dependency("pyodbc", "*")],
        "mysql": [Dependency("mysqlclient", "*")],
        "oracle": [Dependency("cx_oracle", "*")],
        "postgresql": [Dependency("psycopg2", "*")],
        "postgresql-pg8000": [Dependency("pg8000", "*")],
        "postgresql-psycopg2binary": [Dependency("psycopg2-binary", "*")],
        "postgresql-psycopg2cffi": [Dependency("psycopg2cffi", "*")],
        "pymysql": [Dependency("pymysql", "*")],
    }


def test_pypi_repository_supports_reading_bz2_files() -> None:
    repo = MockRepository(fallback=True)

    package = repo.package("twisted", Version.parse("18.9.0"))

    assert package.name == "twisted"
    assert len(package.requires) == 71
    assert sorted(
        (r for r in package.requires if not r.is_optional()), key=lambda r: r.name
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
        "all-non-platform": [
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

    for name in expected_extras.keys():
        assert (
            sorted(package.extras[name], key=lambda r: r.name) == expected_extras[name]
        )


def test_invalid_versions_ignored() -> None:
    repo = MockRepository()

    # the json metadata for this package contains one malformed version
    # and a correct one.
    packages = repo.find_packages(Factory.create_dependency("pygame-music-grid", "*"))
    assert len(packages) == 1


def test_get_should_invalid_cache_on_too_many_redirects_error(
    mocker: MockerFixture,
) -> None:
    delete_cache = mocker.patch("cachecontrol.caches.file_cache.FileCache.delete")

    response = Response()
    response.status_code = 200
    response.encoding = "utf-8"
    response.raw = BytesIO(encode('{"foo": "bar"}'))
    mocker.patch(
        "poetry.utils.authenticator.Authenticator.get",
        side_effect=[TooManyRedirects(), response],
    )
    repository = PyPiRepository()
    repository._get("https://pypi.org/pypi/async-timeout/json")

    assert delete_cache.called


def test_urls() -> None:
    repository = PyPiRepository()

    assert repository.url == "https://pypi.org/simple/"
    assert repository.authenticated_url == "https://pypi.org/simple/"


def test_use_pypi_pretty_name() -> None:
    repo = MockRepository(fallback=True)

    package = repo.find_packages(Factory.create_dependency("twisted", "*"))
    assert len(package) == 1
    assert package[0].pretty_name == "Twisted"


def test_find_links_for_package_of_supported_types():
    repo = MockRepository()
    package = repo.find_packages(Factory.create_dependency("hbmqtt", "0.9.6"))

    assert len(package) == 1

    links = repo.find_links_for_package(package[0])

    assert len(links) == 1
    assert links[0].is_sdist
    assert links[0].show_url == "hbmqtt-0.9.6.tar.gz"


def test_get_release_info_includes_only_supported_types():
    repo = MockRepository()

    release_info = repo._get_release_info(name="hbmqtt", version="0.9.6")

    assert len(release_info["files"]) == 1
    assert release_info["files"][0]["file"] == "hbmqtt-0.9.6.tar.gz"
