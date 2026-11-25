from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.inspection.info import PackageInfo
from poetry.utils.dependency_specification import RequirementsParser


if TYPE_CHECKING:
    from collections.abc import Collection

    from pytest_mock import MockerFixture

    from poetry.utils.cache import ArtifactCache
    from poetry.utils.dependency_specification import DependencySpec


@pytest.mark.parametrize(
    ("requirement", "expected_variants"),
    [
        (
            "git+http://github.com/demo/demo.git",
            ({"git": "http://github.com/demo/demo.git", "name": "demo"},),
        ),
        (
            "git+https://github.com/demo/demo.git",
            ({"git": "https://github.com/demo/demo.git", "name": "demo"},),
        ),
        (
            "git+ssh://github.com/demo/demo.git",
            ({"git": "ssh://github.com/demo/demo.git", "name": "demo"},),
        ),
        (
            "git+https://github.com/demo/demo.git#main",
            (
                {
                    "git": "https://github.com/demo/demo.git",
                    "name": "demo",
                    "rev": "main",
                },
            ),
        ),
        (
            "git+https://github.com/demo/demo.git@main",
            (
                {
                    "git": "https://github.com/demo/demo.git",
                    "name": "demo",
                    "rev": "main",
                },
            ),
        ),
        (
            "git+https://github.com/demo/subdirectories.git@main#subdirectory=two",
            (
                {
                    "git": "https://github.com/demo/subdirectories.git",
                    "name": "two",
                    "rev": "main",
                    "subdirectory": "two",
                },
            ),
        ),
        ("demo", ({"name": "demo"},)),
        ("demo@1.0.0", ({"name": "demo", "version": "1.0.0"},)),
        ("demo@^1.0.0", ({"name": "demo", "version": "^1.0.0"},)),
        ("demo@==1.0.0", ({"name": "demo", "version": "==1.0.0"},)),
        ("demo@!=1.0.0", ({"name": "demo", "version": "!=1.0.0"},)),
        ("demo@~1.0.0", ({"name": "demo", "version": "~1.0.0"},)),
        (
            "demo[a,b]@1.0.0",
            ({"name": "demo", "version": "1.0.0", "extras": ["a", "b"]},),
        ),
        ("demo[a,b]", ({"name": "demo", "extras": ["a", "b"]},)),
        ("../demo", ({"name": "demo", "path": "../demo"},)),
        ("../demo/demo.whl", ({"name": "demo", "path": "../demo/demo.whl"},)),
        (
            "https://files.pythonhosted.org/distributions/demo-0.1.0.tar.gz",
            (
                {
                    "name": "demo",
                    "url": "https://files.pythonhosted.org/distributions/demo-0.1.0.tar.gz",
                },
            ),
        ),
        # PEP 508 inputs
        (
            "poetry-core (>=1.0.7,<1.1.0)",
            ({"name": "poetry-core", "version": ">=1.0.7,<1.1.0"},),
        ),
        (
            'requests [security,tests] >= 2.8.1, == 2.8.* ; python_version < "2.7"',
            (  # allow several equivalent versions to make test more robust
                {
                    "name": "requests",
                    "markers": 'python_version < "2.7"',
                    "version": ">=2.8.1,<2.9",
                    "extras": ["security", "tests"],
                },
                {
                    "name": "requests",
                    "markers": 'python_version < "2.7"',
                    "version": ">=2.8.1,<2.9.0",
                    "extras": ["security", "tests"],
                },
                {
                    "name": "requests",
                    "markers": 'python_version < "2.7"',
                    "version": ">=2.8.1,<2.9.dev0",
                    "extras": ["security", "tests"],
                },
                {
                    "name": "requests",
                    "markers": 'python_version < "2.7"',
                    "version": ">=2.8.1,<2.9.0.dev0",
                    "extras": ["security", "tests"],
                },
                {
                    "name": "requests",
                    "markers": 'python_version < "2.7"',
                    "version": ">=2.8.1,==2.8.*",
                    "extras": ["security", "tests"],
                },
            ),
        ),
        ("name (>=3,<4)", ({"name": "name", "version": ">=3,<4"},)),
        (
            "name@http://foo.com",
            ({"name": "name", "url": "http://foo.com"},),
        ),
        (
            "name [fred,bar] @ http://foo.com ; python_version=='2.7'",
            (
                {
                    "name": "name",
                    "markers": 'python_version == "2.7"',
                    "url": "http://foo.com",
                    "extras": ["bar", "fred"],
                },
            ),
        ),
        (
            (
                'cachecontrol[filecache] (>=0.12.9,<0.13.0); python_version >= "3.6"'
                ' and python_version < "4.0"'
            ),
            (
                {
                    "version": ">=0.12.9,<0.13.0",
                    "markers": 'python_version >= "3.6" and python_version < "4.0"',
                    "extras": ["filecache"],
                    "name": "cachecontrol",
                },
            ),
        ),
    ],
)
def test_parse_dependency_specification(
    requirement: str,
    expected_variants: Collection[DependencySpec],
    mocker: MockerFixture,
    artifact_cache: ArtifactCache,
) -> None:
    original = Path.exists

    # Parsing file and path dependencies reads metadata from the file or path in
    # question: for these tests we mock that out.
    def _mock(self: Path) -> bool:
        if "/" in requirement and self == Path.cwd().joinpath(requirement):
            return True
        return original(self)

    mocker.patch("pathlib.Path.exists", _mock)

    mocker.patch(
        "poetry.inspection.info.get_pep517_metadata",
        return_value=PackageInfo(name="demo", version="0.1.2"),
    )

    assert (
        RequirementsParser(artifact_cache=artifact_cache).parse(requirement)
        in expected_variants
    )


@pytest.mark.parametrize(
    ("requirement", "expected_path"),
    [
        ("./wheels/demo[dev]", "wheels/demo"),
        ("./wheels[1]/demo[dev]", "wheels[1]/demo"),
    ],
)
def test_parse_path_with_trailing_extras(
    requirement: str,
    expected_path: str,
    mocker: MockerFixture,
    artifact_cache: ArtifactCache,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The trailing [dev] is an extra, not part of the path. A bracket earlier
    # in the path must stay put.
    relative = requirement[: requirement.rfind("[")]
    (tmp_path / relative).mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    mocker.patch(
        "poetry.inspection.info.get_pep517_metadata",
        return_value=PackageInfo(name="demo", version="0.1.0"),
    )

    parsed = RequirementsParser(artifact_cache=artifact_cache).parse(requirement)

    assert parsed["name"] == "demo"
    assert parsed["path"] == expected_path
    assert parsed["extras"] == ["dev"]


def test_parse_ipv6_url_with_trailing_extras(
    mocker: MockerFixture,
    artifact_cache: ArtifactCache,
) -> None:
    url = "http://[::1]:8000/demo-0.1.0-py3-none-any.whl"
    package = mocker.Mock()
    package.name = "demo"
    package.source_url = url
    get_package = mocker.patch(
        "poetry.packages.direct_origin.DirectOrigin.get_package_from_url",
        return_value=package,
    )

    parsed = RequirementsParser(artifact_cache=artifact_cache).parse(f"{url}[dev]")

    assert parsed == {"name": "demo", "url": url, "extras": ["dev"]}
    assert get_package.call_args.args[-1] == url
