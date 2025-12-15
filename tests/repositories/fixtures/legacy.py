from __future__ import annotations

import json
import re

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from urllib.parse import urlparse

import pytest
import responses

from packaging.utils import canonicalize_name

from poetry.repositories.legacy_repository import LegacyRepository
from tests.helpers import FIXTURE_PATH_REPOSITORIES_LEGACY
from tests.helpers import FIXTURE_PATH_REPOSITORIES_PYPI


if TYPE_CHECKING:
    from collections.abc import Callable

    from packaging.utils import NormalizedName
    from pytest import FixtureRequest
    from pytest_mock import MockerFixture
    from requests import PreparedRequest

    from poetry.repositories.link_sources.base import LinkSource
    from tests.types import HttpRequestCallback
    from tests.types import HttpResponse
    from tests.types import NormalizedNameTransformer
    from tests.types import SpecializedLegacyRepositoryMocker

pytest_plugins = [
    "tests.repositories.fixtures.python_hosted",
]


@pytest.fixture
def legacy_repository_directory() -> Path:
    return FIXTURE_PATH_REPOSITORIES_LEGACY


@pytest.fixture
def legacy_package_json_locations() -> list[Path]:
    return [
        FIXTURE_PATH_REPOSITORIES_LEGACY / "json",
        FIXTURE_PATH_REPOSITORIES_PYPI / "json",
    ]


@pytest.fixture
def legacy_repository_package_names(legacy_repository_directory: Path) -> set[str]:
    return {
        package_html_file.stem
        for package_html_file in legacy_repository_directory.glob("*.html")
    }


@pytest.fixture
def legacy_repository_index_html(
    legacy_repository_directory: Path, legacy_repository_package_names: set[str]
) -> str:
    hrefs = [
        f'<a href="{name}/">{name}</a><br>' for name in legacy_repository_package_names
    ]

    return f"""<!DOCTYPE html>
    <html>
        <head>
            Legacy Repository
        </head>
        <body>
        {"".join(hrefs)}
        </body>
    </html>
    <!--TIMESTAMP 1709913893-->
    """


@pytest.fixture
def legacy_repository_index_json(
    legacy_repository_directory: Path, legacy_repository_package_names: set[str]
) -> dict[str, Any]:
    names = [{"name": name} for name in legacy_repository_package_names]
    return {"meta": {"api-version": "1.4"}, "projects": names}


@pytest.fixture
def legacy_repository_url() -> str:
    return "https://legacy.foo.bar"


@pytest.fixture
def legacy_repository_html_callback(
    legacy_repository_directory: Path,
    legacy_repository_index_html: str,
) -> HttpRequestCallback:
    def html_callback(request: PreparedRequest) -> HttpResponse:
        assert request.url
        if name := Path(urlparse(request.url).path).name:
            fixture = legacy_repository_directory / f"{name}.html"

            if not fixture.exists():
                return 404, {}, b"Not Found"

            return 200, {}, fixture.read_bytes()

        return 200, {}, legacy_repository_index_html.encode("utf-8")

    return html_callback


@pytest.fixture
def legacy_repository_json_callback(
    legacy_package_json_locations: list[Path],
    legacy_repository_index_json: dict[str, Any],
) -> HttpRequestCallback:
    def json_callback(request: PreparedRequest) -> HttpResponse:
        assert request.url
        headers = {"Content-Type": "application/vnd.pypi.simple.v1+json"}
        if name := Path(urlparse(request.url).path).name:
            fixture = Path()
            for location in legacy_package_json_locations:
                fixture = location / f"{name}.json"
                if fixture.exists():
                    break

            if not fixture.exists():
                return 404, {}, b"Not Found"

            return 200, headers, fixture.read_bytes()

        return 200, headers, json.dumps(legacy_repository_index_json).encode("utf-8")

    return json_callback


@pytest.fixture
def legacy_repository_html(
    http: responses.RequestsMock,
    legacy_repository_url: str,
    legacy_repository_html_callback: HttpRequestCallback,
    mock_files_python_hosted: None,
) -> LegacyRepository:
    http.add_callback(
        responses.GET,
        re.compile(r"^https://legacy\.(.*)+/?(.*)?$"),
        callback=legacy_repository_html_callback,
    )

    return LegacyRepository("legacy", legacy_repository_url, disable_cache=True)


@pytest.fixture
def legacy_repository_json(
    http: responses.RequestsMock,
    legacy_repository_url: str,
    legacy_repository_json_callback: HttpRequestCallback,
    mock_files_python_hosted: None,
) -> LegacyRepository:
    http.add_callback(
        responses.GET,
        re.compile(r"^https://legacy\.(.*)+/?(.*)?$"),
        callback=legacy_repository_json_callback,
    )

    return LegacyRepository("legacy", legacy_repository_url, disable_cache=True)


@pytest.fixture(params=["legacy_repository_html", "legacy_repository_json"])
def legacy_repository(request: FixtureRequest) -> LegacyRepository:
    return request.getfixturevalue(request.param)  # type: ignore[no-any-return]


@pytest.fixture
def specialized_legacy_repository_mocker(
    legacy_repository_html: LegacyRepository,
    legacy_repository_url: str,
    mocker: MockerFixture,
) -> SpecializedLegacyRepositoryMocker:
    """
    This is a mocker factory that allows tests cases to intercept and redirect to special case legacy html files by
    creating an instance of the mocked legacy repository and then mocking its get_page method for special cases.
    """

    def mock(
        transformer_or_suffix: NormalizedNameTransformer | str,
        repository_name: str = "special",
        repository_url: str = legacy_repository_url,
    ) -> LegacyRepository:
        specialized_repository = LegacyRepository(
            repository_name, repository_url, disable_cache=True
        )
        original_get_page = specialized_repository._get_page

        def _mocked_get_page(name: NormalizedName) -> LinkSource:
            return original_get_page(
                canonicalize_name(f"{name}{transformer_or_suffix}")
                if isinstance(transformer_or_suffix, str)
                else transformer_or_suffix(name)
            )

        mocker.patch.object(specialized_repository, "get_page", _mocked_get_page)

        return specialized_repository

    return mock


@pytest.fixture
def legacy_repository_with_extra_packages(
    specialized_legacy_repository_mocker: SpecializedLegacyRepositoryMocker,
) -> LegacyRepository:
    return specialized_legacy_repository_mocker("-with-extra-packages")


@pytest.fixture
def legacy_repository_partial_yank(
    specialized_legacy_repository_mocker: SpecializedLegacyRepositoryMocker,
) -> LegacyRepository:
    return specialized_legacy_repository_mocker("-partial-yank")


@pytest.fixture
def get_legacy_dist_url(legacy_repository_directory: Path) -> Callable[[str], str]:
    def get_url(name: str) -> str:
        package_name = name.split("-", 1)[0]
        path = legacy_repository_directory / f"{package_name}.html"
        if not path.exists():
            raise RuntimeError(
                f"Fixture for {package_name}.html not found in legacy fixtures"
            )
        content = path.read_text(encoding="utf-8")
        match = re.search(rf'<a href="(?P<url>[^"]+{re.escape(name)}[^"]*)"', content)
        if not match:
            raise RuntimeError(
                f"No URL for {name} found in legacy fixture {package_name}.html"
            )
        return match.group("url").split("#", 1)[0]

    return get_url
