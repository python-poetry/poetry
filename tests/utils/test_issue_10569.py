"""Tests for issue #10569: poetry add with || operator in version constraints.

The issue was that RequirementsParser._parse_simple incorrectly split input
strings by the first space found, treating || as the start of the version
string rather than part of the constraint.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.utils.dependency_specification import RequirementsParser


if TYPE_CHECKING:
    from poetry.utils.cache import ArtifactCache


@pytest.mark.parametrize(
    ("requirement", "expected"),
    [
        # Issue #10569: || operator with spaces
        (
            "cachy>=0.1.0 || <0.3.0",
            {"name": "cachy", "version": ">=0.1.0 || <0.3.0"},
        ),
        (
            "requests>=2.0 || <3.0",
            {"name": "requests", "version": ">=2.0 || <3.0"},
        ),
        # Ensure existing formats still work
        ("cachy>=0.1.0", {"name": "cachy", "version": ">=0.1.0"}),
        ("cachy<=0.3.0", {"name": "cachy", "version": "<=0.3.0"}),
        ("cachy>0.1.0", {"name": "cachy", "version": ">0.1.0"}),
        ("cachy<0.3.0", {"name": "cachy", "version": "<0.3.0"}),
        ("cachy!=0.2.0", {"name": "cachy", "version": "!=0.2.0"}),
        ("cachy~0.1.0", {"name": "cachy", "version": "~0.1.0"}),
        ("cachy^0.1.0", {"name": "cachy", "version": "^0.1.0"}),
        # Comma-separated constraints (no spaces)
        ("cachy>=0.1.0,<0.3.0", {"name": "cachy", "version": ">=0.1.0,<0.3.0"}),
        # With extras
        (
            "cachy[extra1]>=0.1.0 || <0.3.0",
            {"name": "cachy", "version": ">=0.1.0 || <0.3.0", "extras": ["extra1"]},
        ),
        (
            "cachy[extra1,extra2]>=0.1.0",
            {"name": "cachy", "version": ">=0.1.0", "extras": ["extra1", "extra2"]},
        ),
    ],
)
def test_parse_simple_with_or_operator(
    requirement: str,
    expected: dict[str, str | list[str]],
    artifact_cache: ArtifactCache,
) -> None:
    """Test that _parse_simple correctly handles || operator in version constraints."""
    parser = RequirementsParser(artifact_cache=artifact_cache)
    result = parser.parse(requirement)
    assert result == expected


@pytest.mark.parametrize(
    ("requirement", "expected"),
    [
        # Space-separated format (package version)
        ("cachy 0.1.0", {"name": "cachy", "version": "0.1.0"}),
        ("cachy latest", {"name": "cachy"}),
        # @ syntax
        ("cachy@0.1.0", {"name": "cachy", "version": "0.1.0"}),
        ("cachy@^1.0.0", {"name": "cachy", "version": "^1.0.0"}),
        # Just package name
        ("cachy", {"name": "cachy"}),
    ],
)
def test_parse_simple_existing_formats_still_work(
    requirement: str,
    expected: dict[str, str],
    artifact_cache: ArtifactCache,
) -> None:
    """Ensure existing formats are not broken by the fix for issue #10569."""
    parser = RequirementsParser(artifact_cache=artifact_cache)
    result = parser.parse(requirement)
    assert result == expected


@pytest.mark.parametrize(
    ("requirement", "expected_name", "expected_version_prefix"),
    [
        # PEP 508 formats - these get parsed and normalized by _parse_pep508
        ("cachy==0.1.0", "cachy", "0.1.0"),
        ("cachy~=0.1.0", "cachy", ">=0.1.0"),  # ~= is normalized
    ],
)
def test_parse_pep508_formats(
    requirement: str,
    expected_name: str,
    expected_version_prefix: str,
    artifact_cache: ArtifactCache,
) -> None:
    """Test PEP 508 formats that get normalized by the parser."""
    parser = RequirementsParser(artifact_cache=artifact_cache)
    result = parser.parse(requirement)
    assert result["name"] == expected_name
    assert str(result.get("version", "")).startswith(expected_version_prefix)
