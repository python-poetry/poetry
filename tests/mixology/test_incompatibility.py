from __future__ import annotations

import pytest

from poetry.core.packages.dependency import Dependency
from poetry.core.packages.url_dependency import URLDependency

from poetry.mixology.incompatibility import Incompatibility
from poetry.mixology.incompatibility_cause import DependencyCause
from poetry.mixology.term import Term


def get_url_dependency(name: str, url: str, version: str) -> URLDependency:
    dependency = URLDependency(name, url)
    dependency.constraint = version  # type: ignore[assignment]
    return dependency


@pytest.mark.parametrize(
    ("dependency1", "dependency2", "expected"),
    [
        (
            Dependency("foo", "1.0"),
            Dependency("bar", "2.0"),
            "foo (1.0) depends on bar (2.0)",
        ),
        (
            Dependency("foo", "1.0"),
            Dependency("bar", "^1.0"),
            "foo (1.0) depends on bar (^1.0)",
        ),
        (
            Dependency("foo", "1.0"),
            get_url_dependency("bar", "https://example.com/bar.whl", "1.1"),
            "foo (1.0) depends on bar (1.1) @ https://example.com/bar.whl",
        ),
        (
            Dependency("foo", "1.0", extras=["bar"]),
            Dependency("foo", "1.0"),
            "foo[bar] (1.0) depends on foo (1.0)",
        ),
    ],
)
def test_str_dependency_cause(
    dependency1: Dependency, dependency2: Dependency, expected: str
) -> None:
    incompatibility = Incompatibility(
        [Term(dependency1, True), Term(dependency2, False)], DependencyCause()
    )
    assert str(incompatibility) == expected
