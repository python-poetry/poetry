from __future__ import annotations

import posixpath

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest
import requests


if TYPE_CHECKING:
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
