from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from packaging.utils import canonicalize_name
from poetry.core.constraints.version import Version
from poetry.core.packages.utils.link import Link

from poetry.repositories.link_sources.html import HTMLPage


if TYPE_CHECKING:
    from tests.types import HTMLPageGetter


@pytest.mark.parametrize(
    "attributes, expected_link",
    [
        ("", Link("https://example.org/demo-0.1.whl")),
        (
            'data-requires-python="&gt;=3.7"',
            Link("https://example.org/demo-0.1.whl", requires_python=">=3.7"),
        ),
        (
            "data-yanked",
            Link("https://example.org/demo-0.1.whl", yanked=True),
        ),
        (
            'data-yanked=""',
            Link("https://example.org/demo-0.1.whl", yanked=True),
        ),
        (
            'data-yanked="&lt;reason&gt;"',
            Link("https://example.org/demo-0.1.whl", yanked="<reason>"),
        ),
        (
            'data-requires-python="&gt;=3.7" data-yanked',
            Link(
                "https://example.org/demo-0.1.whl", requires_python=">=3.7", yanked=True
            ),
        ),
    ],
)
def test_link_attributes(
    html_page_content: HTMLPageGetter, attributes: str, expected_link: Link
) -> None:
    anchor = (
        f'<a href="https://example.org/demo-0.1.whl" {attributes}>demo-0.1.whl</a><br/>'
    )
    content = html_page_content(anchor)
    page = HTMLPage("https://example.org", content)

    assert len(list(page.links)) == 1
    link = next(iter(page.links))
    assert link.url == expected_link.url
    assert link.requires_python == expected_link.requires_python
    assert link.yanked == expected_link.yanked
    assert link.yanked_reason == expected_link.yanked_reason


@pytest.mark.parametrize(
    "yanked_attrs, expected",
    [
        (("", ""), False),
        (("data-yanked", ""), False),
        (("", "data-yanked"), False),
        (("data-yanked", "data-yanked"), True),
        (("data-yanked='reason'", "data-yanked"), "reason"),
        (("data-yanked", "data-yanked='reason'"), "reason"),
        (("data-yanked='reason'", "data-yanked=''"), "reason"),
        (("data-yanked=''", "data-yanked='reason'"), "reason"),
        (("data-yanked='reason'", "data-yanked='reason'"), "reason"),
        (("data-yanked='reason 1'", "data-yanked='reason 2'"), "reason 1\nreason 2"),
    ],
)
def test_yanked(
    html_page_content: HTMLPageGetter,
    yanked_attrs: tuple[str, str],
    expected: bool | str,
) -> None:
    anchors = (
        f'<a href="https://example.org/demo-0.1.tar.gz" {yanked_attrs[0]}>'
        "demo-0.1.tar.gz</a>"
        f'<a href="https://example.org/demo-0.1.whl" {yanked_attrs[1]}>demo-0.1.whl</a>'
    )
    content = html_page_content(anchors)
    page = HTMLPage("https://example.org", content)

    assert page.yanked(canonicalize_name("demo"), Version.parse("0.1")) == expected


@pytest.mark.parametrize(
    ("metadata", "expected_has_metadata", "expected_metadata_hashes"),
    [
        ("", False, {}),
        # new
        ("data-core-metadata", True, {}),
        ("data-core-metadata=''", True, {}),
        ("data-core-metadata='foo'", True, {}),
        ("data-core-metadata='sha256=abcd'", True, {"sha256": "abcd"}),
        # old
        ("data-dist-info-metadata", True, {}),
        ("data-dist-info-metadata=''", True, {}),
        ("data-dist-info-metadata='foo'", True, {}),
        ("data-dist-info-metadata='sha256=abcd'", True, {"sha256": "abcd"}),
        # conflicting (new wins)
        ("data-core-metadata data-dist-info-metadata='sha256=abcd'", True, {}),
        ("data-dist-info-metadata='sha256=abcd' data-core-metadata", True, {}),
        (
            "data-core-metadata='sha256=abcd' data-dist-info-metadata",
            True,
            {"sha256": "abcd"},
        ),
        (
            "data-dist-info-metadata data-core-metadata='sha256=abcd'",
            True,
            {"sha256": "abcd"},
        ),
        (
            "data-core-metadata='sha256=abcd' data-dist-info-metadata='sha256=1234'",
            True,
            {"sha256": "abcd"},
        ),
        (
            "data-dist-info-metadata='sha256=1234' data-core-metadata='sha256=abcd'",
            True,
            {"sha256": "abcd"},
        ),
    ],
)
def test_metadata(
    html_page_content: HTMLPageGetter,
    metadata: str,
    expected_has_metadata: bool,
    expected_metadata_hashes: dict[str, str],
) -> None:
    anchors = f'<a href="https://example.org/demo-0.1.whl" {metadata}>demo-0.1.whl</a>'
    content = html_page_content(anchors)
    page = HTMLPage("https://example.org", content)

    link = next(page.links)
    assert link.has_metadata is expected_has_metadata
    assert link.metadata_hashes == expected_metadata_hashes


@pytest.mark.parametrize(
    "anchor, base_url, expected",
    (
        (
            '<a href="https://example.org/demo-0.1.whl">demo-0.1.whl</a>',
            None,
            "https://example.org/demo-0.1.whl",
        ),
        (
            '<a href="demo-0.1.whl">demo-0.1.whl</a>',
            "https://example.org/",
            "https://example.org/demo-0.1.whl",
        ),
    ),
)
def test_base_url(
    html_page_content: HTMLPageGetter, anchor: str, base_url: str | None, expected: str
) -> None:
    content = html_page_content(anchor, base_url)
    page = HTMLPage("https://example.org", content)
    link = next(iter(page.links))
    assert link.url == expected
