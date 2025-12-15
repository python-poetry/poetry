from __future__ import annotations

import json
import re

from typing import TYPE_CHECKING
from urllib.parse import urlparse

import pytest
import responses

from packaging.utils import parse_sdist_filename
from packaging.utils import parse_wheel_filename

from poetry.repositories.pypi_repository import PyPiRepository
from tests.helpers import FIXTURE_PATH_DISTRIBUTIONS
from tests.helpers import FIXTURE_PATH_REPOSITORIES_PYPI


if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from requests import PreparedRequest

    from tests.types import HttpRequestCallback
    from tests.types import HttpResponse
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


@pytest.fixture
def with_disallowed_pypi_search_html(
    http: responses.RequestsMock, pypi_repository: PyPiRepository
) -> None:
    def search_callback(request: PreparedRequest) -> HttpResponse:
        search_html = FIXTURE_PATH_REPOSITORIES_PYPI.joinpath(
            "search", "search-disallowed.html"
        )
        return 200, {}, search_html.read_bytes()

    search_url_regex = re.compile(r"https://pypi\.org/search(\?(.*))?$")
    http.remove(responses.GET, search_url_regex)
    http.add_callback(
        responses.GET,
        search_url_regex,
        callback=search_callback,
    )


@pytest.fixture(autouse=True)
def pypi_repository(
    http: responses.RequestsMock,
    legacy_repository_html_callback: HttpRequestCallback,
    package_json_locations: list[Path],
    mock_files_python_hosted: None,
) -> PyPiRepository:
    def default_callback(request: PreparedRequest) -> HttpResponse:
        return 404, {}, b"Not Found"

    def search_callback(request: PreparedRequest) -> HttpResponse:
        search_html = FIXTURE_PATH_REPOSITORIES_PYPI.joinpath("search", "search.html")
        return 200, {}, search_html.read_bytes()

    def simple_callback(request: PreparedRequest) -> HttpResponse:
        if request.headers.get("Accept") == "application/vnd.pypi.simple.v1+json":
            return json_callback(request)
        return legacy_repository_html_callback(request)

    def _get_json_filepath(name: str, version: str | None = None) -> Path | None:
        for base in package_json_locations:
            if not version:
                fixture = base / f"{name}.json"
            else:
                fixture = base / name / f"{version}.json"

            if fixture.exists():
                return fixture

        return None

    def json_callback(request: PreparedRequest) -> HttpResponse:
        assert request.url
        path = urlparse(request.url).path
        parts = path.rstrip("/").split("/")[2:]
        name = parts[0]
        version = parts[1] if len(parts) == 3 else None
        fixture = _get_json_filepath(name, version)

        if fixture is None or not fixture.exists():
            return default_callback(request)

        return 200, {}, fixture.read_bytes()

    http.add_callback(
        responses.GET,
        re.compile(r"https://pypi\.org/search(\?(.*))?$"),
        callback=search_callback,
    )

    http.add_callback(
        responses.GET,
        re.compile(r"https://pypi\.org/pypi/(.*)?/json$"),
        callback=json_callback,
    )

    http.add_callback(
        responses.GET,
        re.compile(r"https://pypi\.org/pypi/(?!.*?/json$)(.*)$"),
        callback=default_callback,
    )

    http.add_callback(
        responses.GET,
        re.compile(r"https://pypi\.org/simple/?(.*)?$"),
        callback=simple_callback,
    )

    return PyPiRepository(disable_cache=True, fallback=False)


@pytest.fixture
def get_pypi_dist_url(package_json_locations: list[Path]) -> Callable[[str], str]:
    def get_url(name: str) -> str:
        if name.endswith(".whl"):
            package_name, version, _build, _tags = parse_wheel_filename(name)
        else:
            package_name, version = parse_sdist_filename(name)
        path = package_json_locations[0] / package_name
        if not path.exists():
            raise RuntimeError(
                f"Fixture for {package_name} not found in pypi.org json fixtures"
            )
        path /= f"{version}.json"
        if not path.exists():
            raise RuntimeError(
                f"Fixture for {package_name} {version} not found in pypi.org json fixtures"
            )
        with path.open("rb") as f:
            content = json.load(f)
        for url in content["urls"]:
            if url["filename"] == name:
                url = url["url"]
                assert isinstance(url, str)
                return url
        raise RuntimeError(f"No URL in pypi.org json fixture of {name} {version}")

    return get_url
