from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from deepdiff import DeepDiff

from poetry.utils.dependency_specification import parse_dependency_specification


if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from poetry.utils.dependency_specification import DependencySpec


@pytest.mark.parametrize(
    ("requirement", "specification"),
    [
        (
            "git+https://github.com/demo/demo.git",
            {"git": "https://github.com/demo/demo.git", "name": "demo"},
        ),
        (
            "git+ssh://github.com/demo/demo.git",
            {"git": "ssh://github.com/demo/demo.git", "name": "demo"},
        ),
        (
            "git+https://github.com/demo/demo.git#main",
            {"git": "https://github.com/demo/demo.git", "name": "demo", "rev": "main"},
        ),
        (
            "git+https://github.com/demo/demo.git@main",
            {"git": "https://github.com/demo/demo.git", "name": "demo", "rev": "main"},
        ),
        ("demo", {"name": "demo"}),
        ("demo@1.0.0", {"name": "demo", "version": "1.0.0"}),
        ("demo@^1.0.0", {"name": "demo", "version": "^1.0.0"}),
        ("demo[a,b]@1.0.0", {"name": "demo", "version": "1.0.0", "extras": ["a", "b"]}),
        ("demo[a,b]", {"name": "demo", "extras": ["a", "b"]}),
        ("../demo", {"name": "demo", "path": "../demo"}),
        ("../demo/demo.whl", {"name": "demo", "path": "../demo/demo.whl"}),
        (
            "https://example.com/packages/demo-0.1.0.tar.gz",
            {"name": "demo", "url": "https://example.com/packages/demo-0.1.0.tar.gz"},
        ),
    ],
)
def test_parse_dependency_specification(
    requirement: str, specification: DependencySpec, mocker: MockerFixture
) -> None:
    original = Path.exists

    def _mock(self: Path) -> bool:
        if "/" in requirement and self == Path.cwd().joinpath(requirement):
            return True
        return original(self)

    mocker.patch("pathlib.Path.exists", _mock)

    assert not DeepDiff(parse_dependency_specification(requirement), specification)
