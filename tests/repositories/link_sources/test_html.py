from __future__ import annotations

import pytest

from packaging.utils import canonicalize_name
from poetry.core.constraints.version import Version
from poetry.core.packages.utils.link import Link

from poetry.repositories.link_sources.html import HTMLPage


DEMO_TEMPLATE = """
<!DOCTYPE html>
<html>
  <head>
    <meta name="pypi:repository-version" content="1.0">
    <title>Links for demo</title>
  </head>
  <body>
    <h1>Links for demo</h1>
    {}
    </body>
</html>
"""


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
def test_link_attributes(attributes: str, expected_link: Link) -> None:
    anchor = (
        f'<a href="https://example.org/demo-0.1.whl" {attributes}>demo-0.1.whl</a><br/>'
    )
    content = DEMO_TEMPLATE.format(anchor)
    page = HTMLPage("https://example.org", content)

    assert len(list(page.links)) == 1
    link = list(page.links)[0]
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
def test_yanked(yanked_attrs: tuple[str, str], expected: bool | str) -> None:
    anchors = (
        f'<a href="https://example.org/demo-0.1.tar.gz" {yanked_attrs[0]}>'
        "demo-0.1.tar.gz</a>"
        f'<a href="https://example.org/demo-0.1.whl" {yanked_attrs[1]}>demo-0.1.whl</a>'
    )
    content = DEMO_TEMPLATE.format(anchors)
    page = HTMLPage("https://example.org", content)

    assert page.yanked(canonicalize_name("demo"), Version.parse("0.1")) == expected
