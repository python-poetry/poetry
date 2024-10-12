from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.repositories.parsers.html_page_parser import HTMLPageParser


if TYPE_CHECKING:
    from tests.types import HTMLPageGetter


@pytest.fixture()
def html_page(html_page_content: HTMLPageGetter) -> str:
    links = """
        <a href="https://example.org/demo-0.1.whl">demo-0.1.whl</a><br/>
        <a href="https://example.org/demo-0.1.whl"
            data-requires-python=">=3.7">demo-0.1.whl</a><br/>
        <a href="https://example.org/demo-0.1.whl" data-yanked>demo-0.1.whl</a><br/>
        <a href="https://example.org/demo-0.1.whl" data-yanked="">demo-0.1.whl</a><br/>
        <a href="https://example.org/demo-0.1.whl"
            data-yanked="<reason>"
        >demo-0.1.whl</a><br/>
        <a href="https://example.org/demo-0.1.whl"
            data-requires-python=">=3.7"
            data-yanked
         >demo-0.1.whl</a><br/>
    """
    return html_page_content(links)


def test_html_page_parser_anchors(html_page: str) -> None:
    parser = HTMLPageParser()
    parser.feed(html_page)

    assert parser.anchors == [
        {"href": "https://example.org/demo-0.1.whl"},
        {"data-requires-python": ">=3.7", "href": "https://example.org/demo-0.1.whl"},
        {"data-yanked": None, "href": "https://example.org/demo-0.1.whl"},
        {"data-yanked": "", "href": "https://example.org/demo-0.1.whl"},
        {"data-yanked": "<reason>", "href": "https://example.org/demo-0.1.whl"},
        {
            "data-requires-python": ">=3.7",
            "data-yanked": None,
            "href": "https://example.org/demo-0.1.whl",
        },
    ]


def test_html_page_parser_base_url() -> None:
    content = """
        <!DOCTYPE html>
        <html>
          <head>
            <base href="https://example.org/">
            <meta name="pypi:repository-version" content="1.0">
            <title>Links for demo</title>
          </head>
          <body>
            <h1>Links for demo</h1>
            <a href="demo-0.1.whl">demo-0.1.whl</a><br/>
            </body>
        </html>
    """
    parser = HTMLPageParser()
    parser.feed(content)

    assert parser.base_url == "https://example.org/"
