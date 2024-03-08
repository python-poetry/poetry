from __future__ import annotations

import posixpath
import re

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from urllib.parse import urlparse

import pytest
import requests


if TYPE_CHECKING:
    from httpretty import httpretty
    from httpretty.core import HTTPrettyRequest

    from tests.types import HTMLPageGetter
    from tests.types import RequestsSessionGet


@pytest.fixture
def html_page_content() -> HTMLPageGetter:
    def _fixture(content: str, base_url: str | None = None) -> str:
        base = f'<base href="{base_url}"' if base_url else ""
        return f"""
        <!DOCTYPE html>
        <html>
          <head>
            {base}
            <meta name="pypi:repository-version" content="1.0">
            <title>Links for demo</title>
          </head>
          <body>
            <h1>Links for demo</h1>
            {content}
            </body>
        </html>
        """

    return _fixture


@pytest.fixture
def get_metadata_mock() -> RequestsSessionGet:
    def metadata_mock(url: str, **__: Any) -> requests.Response:
        if url.endswith(".metadata"):
            response = requests.Response()
            response.encoding = "application/text"
            response._content = (
                (
                    Path(__file__).parent
                    / "fixtures"
                    / "metadata"
                    / posixpath.basename(url)
                )
                .read_text()
                .encode()
            )
            return response
        raise requests.HTTPError()

    return metadata_mock


@pytest.fixture(scope="session")
def legacy_repository_directory() -> Path:
    return Path(__file__).parent / "fixtures" / "legacy"


@pytest.fixture(scope="session")
def legacy_repository_package_names(legacy_repository_directory: Path) -> set[str]:
    return {
        package_html_file.stem
        for package_html_file in legacy_repository_directory.glob("*.html")
    }


@pytest.fixture(scope="session")
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


@pytest.fixture(scope="session")
def legacy_repository_url() -> str:
    return "https://legacy.foo.bar"


@pytest.fixture
def mock_http_legacy_repository(
    http: type[httpretty],
    legacy_repository_url: str,
    legacy_repository_directory: Path,
    legacy_repository_index_html: str,
) -> None:
    def file_callback(
        request: HTTPrettyRequest, uri: str, headers: dict[str, Any]
    ) -> list[int | dict[str, Any] | bytes]:
        name = Path(urlparse(uri).path).name
        fixture = legacy_repository_directory.parent / "pypi.org" / "dists" / name

        if not fixture.exists():
            return [404, headers, b"Not Found"]

        return [200, headers, fixture.read_bytes()]

    http.register_uri(
        http.GET,
        re.compile("^https://files.pythonhosted.org/.*$"),
        body=file_callback,
    )

    def html_callback(
        request: HTTPrettyRequest, uri: str, headers: dict[str, Any]
    ) -> list[int | dict[str, Any] | bytes]:
        url_path = urlparse(uri).path

        if name := url_path.strip("/"):
            fixture = legacy_repository_directory / f"{name}.html"

            if not fixture.exists():
                return [404, headers, b"Not Found"]

            return [200, headers, fixture.read_bytes()]

        return [200, headers, legacy_repository_index_html.encode("utf-8")]

    http.register_uri(
        http.GET,
        re.compile(f"^{legacy_repository_url}/?(.*)?$"),
        body=html_callback,
    )
