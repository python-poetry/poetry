from __future__ import annotations

import re

from typing import TYPE_CHECKING
from typing import Any
from urllib.parse import urlparse

import pytest

from poetry.repositories.pypi_repository import PyPiRepository
from tests.helpers import FIXTURE_PATH_DISTRIBUTIONS
from tests.helpers import FIXTURE_PATH_REPOSITORIES_PYPI


if TYPE_CHECKING:
    from pathlib import Path

    import httpretty

    from httpretty.core import HTTPrettyRequest

    from tests.types import HTTPrettyRequestCallback
    from tests.types import HTTPrettyResponse
    from tests.types import PackageDistributionLookup


pytest_plugins = [
    "tests.repositories.fixtures.legacy",
    "tests.repositories.fixtures.python_hosted",
]


@pytest.fixture
def package_distribution_locations() -> list[Path]:
    return [
        FIXTURE_PATH_REPOSITORIES_PYPI / "dists",
        FIXTURE_PATH_REPOSITORIES_PYPI / "dists" / "mocked",
        FIXTURE_PATH_REPOSITORIES_PYPI / "stubbed",
        FIXTURE_PATH_DISTRIBUTIONS,
    ]


@pytest.fixture
def package_json_locations() -> list[Path]:
    return [
        FIXTURE_PATH_REPOSITORIES_PYPI / "json",
        FIXTURE_PATH_REPOSITORIES_PYPI / "json" / "mocked",
    ]


@pytest.fixture
def package_metadata_locations() -> list[Path]:
    return [
        FIXTURE_PATH_REPOSITORIES_PYPI / "metadata",
        FIXTURE_PATH_REPOSITORIES_PYPI / "metadata" / "mocked",
    ]


@pytest.fixture
def package_distribution_lookup(
    package_distribution_locations: list[Path],
) -> PackageDistributionLookup:
    def lookup(name: str) -> Path | None:
        for location in package_distribution_locations:
            fixture = location / name
            if fixture.exists():
                return fixture
        return None

    return lookup


@pytest.fixture(autouse=True)
def pypi_repository(
    http: type[httpretty],
    legacy_repository_html_callback: HTTPrettyRequestCallback,
    package_json_locations: list[Path],
    mock_files_python_hosted: None,
) -> PyPiRepository:
    def default_callback(
        request: HTTPrettyRequest, uri: str, headers: dict[str, Any]
    ) -> HTTPrettyResponse:
        return 404, headers, b"Not Found"

    def search_callback(
        request: HTTPrettyRequest, uri: str, headers: dict[str, Any]
    ) -> HTTPrettyResponse:
        search_html = FIXTURE_PATH_REPOSITORIES_PYPI.joinpath("search", "search.html")
        return 200, headers, search_html.read_bytes()

    def simple_callback(
        request: HTTPrettyRequest, uri: str, headers: dict[str, Any]
    ) -> HTTPrettyResponse:
        if request.headers["Accept"] == "application/vnd.pypi.simple.v1+json":
            return json_callback(request, uri, headers)
        return legacy_repository_html_callback(request, uri, headers)

    def _get_json_filepath(name: str, version: str | None = None) -> Path | None:
        for base in package_json_locations:
            if not version:
                fixture = base / f"{name}.json"
            else:
                fixture = base / name / f"{version}.json"

            if fixture.exists():
                return fixture

        return None

    def json_callback(
        request: HTTPrettyRequest, uri: str, headers: dict[str, Any]
    ) -> HTTPrettyResponse:
        path = urlparse(uri).path
        parts = path.rstrip("/").split("/")[2:]
        name = parts[0]
        version = parts[1] if len(parts) == 3 else None
        fixture = _get_json_filepath(name, version)

        if fixture is None or not fixture.exists():
            return default_callback(request, uri, headers)

        return 200, headers, fixture.read_bytes()

    http.register_uri(
        http.GET,
        re.compile(r"https://pypi.org/search(\?(.*))?$"),
        body=search_callback,
    )

    http.register_uri(
        http.GET,
        re.compile(r"https://pypi.org/pypi/(.*)?/json$"),
        body=json_callback,
    )

    http.register_uri(
        http.GET,
        re.compile(r"https://pypi.org/pypi/(.*)?(?!/json)$"),
        body=default_callback,
    )

    http.register_uri(
        http.GET,
        re.compile(r"https://pypi.org/simple/?(.*)?$"),
        body=simple_callback,
    )

    return PyPiRepository(disable_cache=True, fallback=False)
