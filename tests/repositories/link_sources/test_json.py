from __future__ import annotations

import pytest

from poetry.repositories.link_sources.json import SimpleJsonPage


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
