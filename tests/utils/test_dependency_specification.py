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
        (
            "git+https://github.com/demo/subdirectories.git@main#subdirectory=two",
            {
                "git": "https://github.com/demo/subdirectories.git",
                "name": "two",
                "rev": "main",
                "subdirectory": "two",
            },
        ),
        ("demo", {"name": "demo"}),
        ("demo@1.0.0", {"name": "demo", "version": "1.0.0"}),
        ("demo@^1.0.0", {"name": "demo", "version": "^1.0.0"}),
        ("demo@==1.0.0", {"name": "demo", "version": "==1.0.0"}),
        ("demo@!=1.0.0", {"name": "demo", "version": "!=1.0.0"}),
        ("demo@~1.0.0", {"name": "demo", "version": "~1.0.0"}),
        ("demo[a,b]@1.0.0", {"name": "demo", "version": "1.0.0", "extras": ["a", "b"]}),
        ("demo[a,b]", {"name": "demo", "extras": ["a", "b"]}),
        ("../demo", {"name": "demo", "path": "../demo"}),
        ("../demo/demo.whl", {"name": "demo", "path": "../demo/demo.whl"}),
        (
            "https://example.com/distributions/demo-0.1.0.tar.gz",
            {
                "name": "demo",
                "url": "https://example.com/distributions/demo-0.1.0.tar.gz",
            },
        ),
        # PEP 508 inputs
        (
            "poetry-core (>=1.0.7,<1.1.0)",
            {"name": "poetry-core", "version": ">=1.0.7,<1.1.0"},
        ),
        (
            'requests [security,tests] >= 2.8.1, == 2.8.* ; python_version < "2.7"',
            {
                "name": "requests",
                "markers": 'python_version < "2.7"',
                "version": ">=2.8.1,<2.9.0",
                "extras": ["security", "tests"],
            },
        ),
        ("name (>=3,<4)", {"name": "name", "version": ">=3,<4"}),
        (
            "name@http://foo.com",
            {"name": "name", "url": "http://foo.com"},
        ),
        (
            "name [fred,bar] @ http://foo.com ; python_version=='2.7'",
            {
                "name": "name",
                "markers": 'python_version == "2.7"',
                "url": "http://foo.com",
                "extras": ["fred", "bar"],
            },
        ),
        (
            (
                'cachecontrol[filecache] (>=0.12.9,<0.13.0); python_version >= "3.6"'
                ' and python_version < "4.0"'
            ),
            {
                "version": ">=0.12.9,<0.13.0",
                "markers": 'python_version >= "3.6" and python_version < "4.0"',
                "extras": ["filecache"],
                "name": "cachecontrol",
            },
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

    assert not DeepDiff(
        parse_dependency_specification(requirement), specification, ignore_order=True
    )
