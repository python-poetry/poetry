from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from tests.types import HTMLPageGetter


@pytest.fixture
def html_page_content() -> HTMLPageGetter:
    def _fixture(content: str, base_url: str | None = None) -> str:
        base = f'<base href="{base_url}"' if base_url else ""
        return """
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
        """.format(content=content, base=base)

    return _fixture
