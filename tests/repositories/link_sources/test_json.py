from __future__ import annotations

import pytest

from packaging.utils import canonicalize_name
from poetry.core.constraints.version.version import Version

from poetry.repositories.link_sources.json import SimpleJsonPage
from poetry.repositories.link_sources.json import SimpleRepositoryJsonRootPage


@pytest.fixture
def root_page() -> SimpleRepositoryJsonRootPage:
    names = ["poetry", "poetry-core", "requests"]

    return SimpleRepositoryJsonRootPage(
        {
            "meta": {"api-version": "1.4"},
            "projects": [{"name": name} for name in names],
        }
    )


def test_root_page_package_names(root_page: SimpleRepositoryJsonRootPage) -> None:
    assert root_page.package_names == ["poetry", "poetry-core", "requests"]


def test_attributes() -> None:
    content = {
        "files": [
            # minimal
            {"url": "https://example.org/demo-0.1.whl"},
            # all (with non-default values)
            {
                "url": "https://example.org/demo-0.1.tar.gz",
                "requires-python": ">=3.6",
                "yanked": True,
                "hashes": {"sha256": "abcd1234"},
                "core-metadata": True,
            },
        ]
    }
    page = SimpleJsonPage("https://example.org", content)

    assert page.url == "https://example.org"
    links = list(page.links)
    assert len(links) == 2

    assert links[0].url == "https://example.org/demo-0.1.whl"
    assert links[0].requires_python is None
    assert links[0].yanked is False
    assert links[0].hashes == {}
    assert links[0].has_metadata is False

    assert links[1].url == "https://example.org/demo-0.1.tar.gz"
    assert links[1].requires_python == ">=3.6"
    assert links[1].yanked is True
    assert links[1].hashes == {"sha256": "abcd1234"}
    assert links[1].has_metadata is True


@pytest.mark.parametrize(
    ("yanked", "expected"),
    [
        ((None, None), False),
        ((False, False), False),
        ((True, False), False),
        ((False, True), False),
        ((True, True), True),
        (("reason", True), "reason"),
        ((True, "reason"), "reason"),
        (("reason", "reason"), "reason"),
        (("reason 1", "reason 2"), "reason 1\nreason 2"),
    ],
)
def test_yanked(
    yanked: tuple[str | None, str | None],
    expected: bool | str,
) -> None:
    content = {
        "files": [
            {"url": "https://example.org/demo-0.1.tar.gz", "yanked": yanked[0]},
            {"url": "https://example.org/demo-0.1.whl", "yanked": yanked[1]},
        ]
    }
    if yanked[0] is None:
        del content["files"][0]["yanked"]
    if yanked[1] is None:
        del content["files"][1]["yanked"]
    page = SimpleJsonPage("https://example.org", content)

    assert page.yanked(canonicalize_name("demo"), Version.parse("0.1")) == expected


@pytest.mark.parametrize(
    ("metadata", "expected_has_metadata", "expected_metadata_hashes"),
    [
        ({}, False, {}),
        # new
        ({"core-metadata": False}, False, {}),
        ({"core-metadata": True}, True, {}),
        (
            {"core-metadata": {"sha1": "1234", "sha256": "abcd"}},
            True,
            {"sha1": "1234", "sha256": "abcd"},
        ),
        ({"core-metadata": {}}, False, {}),
        (
            {"core-metadata": {"sha1": "1234", "sha256": "abcd"}},
            True,
            {"sha1": "1234", "sha256": "abcd"},
        ),
        # old
        ({"dist-info-metadata": False}, False, {}),
        ({"dist-info-metadata": True}, True, {}),
        ({"dist-info-metadata": {"sha256": "abcd"}}, True, {"sha256": "abcd"}),
        ({"dist-info-metadata": {}}, False, {}),
        (
            {"dist-info-metadata": {"sha1": "1234", "sha256": "abcd"}},
            True,
            {"sha1": "1234", "sha256": "abcd"},
        ),
        # conflicting (new wins)
        ({"core-metadata": False, "dist-info-metadata": True}, False, {}),
        (
            {"core-metadata": False, "dist-info-metadata": {"sha256": "abcd"}},
            False,
            {},
        ),
        ({"core-metadata": True, "dist-info-metadata": False}, True, {}),
        (
            {"core-metadata": True, "dist-info-metadata": {"sha256": "abcd"}},
            True,
            {},
        ),
        (
            {"core-metadata": {"sha256": "abcd"}, "dist-info-metadata": False},
            True,
            {"sha256": "abcd"},
        ),
        (
            {"core-metadata": {"sha256": "abcd"}, "dist-info-metadata": True},
            True,
            {"sha256": "abcd"},
        ),
        (
            {
                "core-metadata": {"sha256": "abcd"},
                "dist-info-metadata": {"sha256": "1234"},
            },
            True,
            {"sha256": "abcd"},
        ),
    ],
)
def test_metadata(
    metadata: dict[str, bool | dict[str, str]],
    expected_has_metadata: bool,
    expected_metadata_hashes: dict[str, str],
) -> None:
    content = {"files": [{"url": "https://example.org/demo-0.1.whl", **metadata}]}
    page = SimpleJsonPage("https://example.org", content)

    link = next(page.links)
    assert link.has_metadata is expected_has_metadata
    assert link.metadata_hashes == expected_metadata_hashes


@pytest.mark.parametrize(
    ("url", "repo_url", "expected"),
    (
        (
            "https://example.org/files/demo-0.1.whl",
            "https://example.org/simple/",
            "https://example.org/files/demo-0.1.whl",
        ),
        (
            "demo-0.1.whl",
            "https://example.org/simple/",
            "https://example.org/simple/demo-0.1.whl",
        ),
    ),
)
def test_base_url(url: str, repo_url: str, expected: str) -> None:
    page = SimpleJsonPage(repo_url, {"files": [{"url": url}]})
    link = next(iter(page.links))
    assert link.url == expected
