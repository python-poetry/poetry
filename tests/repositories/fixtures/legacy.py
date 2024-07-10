from __future__ import annotations

import re

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from urllib.parse import urlparse

import pytest

from packaging.utils import canonicalize_name

from poetry.repositories.legacy_repository import LegacyRepository
from tests.helpers import FIXTURE_PATH_REPOSITORIES_LEGACY


if TYPE_CHECKING:
    import httpretty

    from httpretty.core import HTTPrettyRequest
    from packaging.utils import NormalizedName
    from pytest_mock import MockerFixture

    from poetry.repositories.link_sources.html import HTMLPage
    from tests.types import HTTPrettyRequestCallback
    from tests.types import NormalizedNameTransformer
    from tests.types import SpecializedLegacyRepositoryMocker

pytest_plugins = [
    "tests.repositories.fixtures.python_hosted",
]


@pytest.fixture
def legacy_repository_directory() -> Path:
    return FIXTURE_PATH_REPOSITORIES_LEGACY


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
def legacy_repository_url() -> str:
    return "https://legacy.foo.bar"


@pytest.fixture
def legacy_repository_html_callback(
    legacy_repository_directory: Path,
    legacy_repository_index_html: str,
) -> HTTPrettyRequestCallback:
    def html_callback(
        request: HTTPrettyRequest, uri: str, headers: dict[str, Any]
    ) -> tuple[int, dict[str, Any], bytes]:
        if name := Path(urlparse(uri).path).name:
            fixture = legacy_repository_directory / f"{name}.html"

            if not fixture.exists():
                return 404, headers, b"Not Found"

            return 200, headers, fixture.read_bytes()

        return 200, headers, legacy_repository_index_html.encode("utf-8")

    return html_callback


@pytest.fixture
def legacy_repository(
    http: type[httpretty],
    legacy_repository_url: str,
    legacy_repository_html_callback: HTTPrettyRequestCallback,
    mock_files_python_hosted: None,
) -> LegacyRepository:
    http.register_uri(
        http.GET,
        re.compile("^https://legacy.(.*)+/?(.*)?$"),
        body=legacy_repository_html_callback,
    )

    return LegacyRepository("legacy", legacy_repository_url, disable_cache=True)


@pytest.fixture
def specialized_legacy_repository_mocker(
    legacy_repository: LegacyRepository,
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

        def _mocked_get_page(name: NormalizedName) -> HTMLPage:
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
