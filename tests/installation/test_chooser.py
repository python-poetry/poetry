from __future__ import annotations

import re

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest

from packaging.tags import Tag
from poetry.core.packages.package import Package

from poetry.installation.chooser import Chooser
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.repositories.pypi_repository import PyPiRepository
from poetry.repositories.repository_pool import RepositoryPool
from poetry.utils.env import MockEnv


if TYPE_CHECKING:
    import httpretty

    from httpretty.core import HTTPrettyRequest

    from tests.conftest import Config


JSON_FIXTURES = (
    Path(__file__).parent.parent / "repositories" / "fixtures" / "pypi.org" / "json"
)

LEGACY_FIXTURES = Path(__file__).parent.parent / "repositories" / "fixtures" / "legacy"


@pytest.fixture()
def env() -> MockEnv:
    return MockEnv(
        supported_tags=[
            Tag("cp37", "cp37", "macosx_10_15_x86_64"),
            Tag("py3", "none", "any"),
        ]
    )


@pytest.fixture()
def mock_pypi(http: type[httpretty.httpretty]) -> None:
    def callback(
        request: HTTPrettyRequest, uri: str, headers: dict[str, Any]
    ) -> list[int | dict[str, Any] | str] | None:
        parts = uri.rsplit("/")

        name = parts[-3]
        version = parts[-2]

        fixture = JSON_FIXTURES / name / (version + ".json")
        if not fixture.exists():
            fixture = JSON_FIXTURES / (name + ".json")

        if not fixture.exists():
            return None

        with fixture.open(encoding="utf-8") as f:
            return [200, headers, f.read()]

    http.register_uri(
        http.GET,
        re.compile("^https://pypi.org/(.+?)/(.+?)/json$"),
        body=callback,
    )


@pytest.fixture()
def mock_legacy(http: type[httpretty.httpretty]) -> None:
    def callback(
        request: HTTPrettyRequest, uri: str, headers: dict[str, Any]
    ) -> list[int | dict[str, Any] | str]:
        parts = uri.rsplit("/")
        name = parts[-2]

        fixture = LEGACY_FIXTURES / (name + ".html")

        with fixture.open(encoding="utf-8") as f:
            return [200, headers, f.read()]

    http.register_uri(
        http.GET,
        re.compile("^https://foo.bar/simple/(.+?)$"),
        body=callback,
    )


@pytest.fixture()
def mock_legacy_partial_yank(http: type[httpretty.httpretty]) -> None:
    def callback(
        request: HTTPrettyRequest, uri: str, headers: dict[str, Any]
    ) -> list[int | dict[str, Any] | str]:
        parts = uri.rsplit("/")
        name = parts[-2]

        fixture = LEGACY_FIXTURES / (name + "-partial-yank" + ".html")

        with fixture.open(encoding="utf-8") as f:
            return [200, headers, f.read()]

    http.register_uri(
        http.GET,
        re.compile("^https://foo2.bar/simple/(.+?)$"),
        body=callback,
    )


@pytest.fixture()
def pool() -> RepositoryPool:
    pool = RepositoryPool()

    pool.add_repository(PyPiRepository(disable_cache=True))
    pool.add_repository(
        LegacyRepository("foo", "https://foo.bar/simple/", disable_cache=True)
    )
    pool.add_repository(
        LegacyRepository("foo2", "https://foo2.bar/simple/", disable_cache=True)
    )

    return pool


@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_chooses_universal_wheel_link_if_available(
    env: MockEnv,
    mock_pypi: None,
    mock_legacy: None,
    source_type: str,
    pool: RepositoryPool,
) -> None:
    chooser = Chooser(pool, env)

    package = Package("pytest", "3.5.0")
    if source_type == "legacy":
        package = Package(
            package.name,
            package.version.text,
            source_type="legacy",
            source_reference="foo",
            source_url="https://foo.bar/simple/",
        )

    link = chooser.choose_for(package)

    assert link.filename == "pytest-3.5.0-py2.py3-none-any.whl"


@pytest.mark.parametrize(
    ("policy", "filename"),
    [
        (":all:", "pytest-3.5.0.tar.gz"),
        (":none:", "pytest-3.5.0-py2.py3-none-any.whl"),
        ("black", "pytest-3.5.0-py2.py3-none-any.whl"),
        ("pytest", "pytest-3.5.0.tar.gz"),
        ("pytest,black", "pytest-3.5.0.tar.gz"),
    ],
)
@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_no_binary_policy(
    env: MockEnv,
    mock_pypi: None,
    mock_legacy: None,
    source_type: str,
    pool: RepositoryPool,
    policy: str,
    filename: str,
    config: Config,
) -> None:
    config.merge({"installer": {"no-binary": policy.split(",")}})

    chooser = Chooser(pool, env, config)

    package = Package("pytest", "3.5.0")
    if source_type == "legacy":
        package = Package(
            package.name,
            package.version.text,
            source_type="legacy",
            source_reference="foo",
            source_url="https://foo.bar/simple/",
        )

    link = chooser.choose_for(package)

    assert link.filename == filename


@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_chooses_specific_python_universal_wheel_link_if_available(
    env: MockEnv,
    mock_pypi: None,
    mock_legacy: None,
    source_type: str,
    pool: RepositoryPool,
) -> None:
    chooser = Chooser(pool, env)

    package = Package("isort", "4.3.4")
    if source_type == "legacy":
        package = Package(
            package.name,
            package.version.text,
            source_type="legacy",
            source_reference="foo",
            source_url="https://foo.bar/simple/",
        )

    link = chooser.choose_for(package)

    assert link.filename == "isort-4.3.4-py3-none-any.whl"


@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_chooses_system_specific_wheel_link_if_available(
    mock_pypi: None, mock_legacy: None, source_type: str, pool: RepositoryPool
) -> None:
    env = MockEnv(
        supported_tags=[Tag("cp37", "cp37m", "win32"), Tag("py3", "none", "any")]
    )
    chooser = Chooser(pool, env)

    package = Package("pyyaml", "3.13.0")
    if source_type == "legacy":
        package = Package(
            package.name,
            package.version.text,
            source_type="legacy",
            source_reference="foo",
            source_url="https://foo.bar/simple/",
        )

    link = chooser.choose_for(package)

    assert link.filename == "PyYAML-3.13-cp37-cp37m-win32.whl"


@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_chooses_sdist_if_no_compatible_wheel_link_is_available(
    env: MockEnv,
    mock_pypi: None,
    mock_legacy: None,
    source_type: str,
    pool: RepositoryPool,
) -> None:
    chooser = Chooser(pool, env)

    package = Package("pyyaml", "3.13.0")
    if source_type == "legacy":
        package = Package(
            package.name,
            package.version.text,
            source_type="legacy",
            source_reference="foo",
            source_url="https://foo.bar/simple/",
        )

    link = chooser.choose_for(package)

    assert link.filename == "PyYAML-3.13.tar.gz"


@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_chooses_distributions_that_match_the_package_hashes(
    env: MockEnv,
    mock_pypi: None,
    mock_legacy: None,
    source_type: str,
    pool: RepositoryPool,
) -> None:
    chooser = Chooser(pool, env)

    package = Package("isort", "4.3.4")
    files = [
        {
            "hash": (
                "sha256:b9c40e9750f3d77e6e4d441d8b0266cf555e7cdabdcff33c4fd06366ca761ef8"
            ),
            "filename": "isort-4.3.4.tar.gz",
        }
    ]
    if source_type == "legacy":
        package = Package(
            package.name,
            package.version.text,
            source_type="legacy",
            source_reference="foo",
            source_url="https://foo.bar/simple/",
        )

    package.files = files

    link = chooser.choose_for(package)

    assert link.filename == "isort-4.3.4.tar.gz"


@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_chooses_yanked_if_no_others(
    env: MockEnv,
    mock_pypi: None,
    mock_legacy: None,
    source_type: str,
    pool: RepositoryPool,
) -> None:
    chooser = Chooser(pool, env)

    package = Package("black", "21.11b0")
    files = [
        {
            "filename": "black-21.11b0-py3-none-any.whl",
            "hash": (
                "sha256:0b1f66cbfadcd332ceeaeecf6373d9991d451868d2e2219ad0ac1213fb701117"
            ),
        }
    ]
    if source_type == "legacy":
        package = Package(
            package.name,
            package.version.text,
            source_type="legacy",
            source_reference="foo",
            source_url="https://foo.bar/simple/",
        )

    package.files = files

    link = chooser.choose_for(package)

    assert link.filename == "black-21.11b0-py3-none-any.whl"
    assert link.yanked


def test_chooser_does_not_choose_yanked_if_others(
    mock_legacy: None,
    mock_legacy_partial_yank: None,
    pool: RepositoryPool,
) -> None:
    chooser = Chooser(pool, MockEnv(supported_tags=[Tag("py2", "none", "any")]))

    package = Package("futures", "3.2.0")
    files = [
        {
            "filename": "futures-3.2.0-py2-none-any.whl",
            "hash": "sha256:ec0a6cb848cc212002b9828c3e34c675e0c9ff6741dc445cab6fdd4e1085d1f1",
        },
        {
            "filename": "futures-3.2.0.tar.gz",
            "hash": "sha256:9ec02aa7d674acb8618afb127e27fde7fc68994c0437ad759fa094a574adb265",
        },
    ]
    package = Package(
        package.name,
        package.version.text,
        source_type="legacy",
        source_reference="foo",
        source_url="https://foo.bar/simple/",
    )
    package_partial_yank = Package(
        package.name,
        package.version.text,
        source_type="legacy",
        source_reference="foo2",
        source_url="https://foo2.bar/simple/",
    )

    package.files = files
    package_partial_yank.files = files

    link = chooser.choose_for(package)
    link_partial_yank = chooser.choose_for(package_partial_yank)

    assert link.filename == "futures-3.2.0-py2-none-any.whl"
    assert link_partial_yank.filename == "futures-3.2.0.tar.gz"


@pytest.mark.parametrize("source_type", ["", "legacy"])
def test_chooser_throws_an_error_if_package_hashes_do_not_match(
    env: MockEnv,
    mock_pypi: None,
    mock_legacy: None,
    source_type: None,
    pool: RepositoryPool,
) -> None:
    chooser = Chooser(pool, env)

    package = Package("isort", "4.3.4")
    files = [
        {
            "hash": (
                "sha256:0000000000000000000000000000000000000000000000000000000000000000"
            ),
            "filename": "isort-4.3.4.tar.gz",
        }
    ]
    if source_type == "legacy":
        package = Package(
            package.name,
            package.version.text,
            source_type="legacy",
            source_reference="foo",
            source_url="https://foo.bar/simple/",
        )

    package.files = files

    with pytest.raises(RuntimeError) as e:
        chooser.choose_for(package)
    assert files[0]["hash"] in str(e)


@pytest.mark.usefixtures("mock_legacy")
def test_chooser_md5_remote_fallback_to_sha256_inline_calculation(
    env: MockEnv, pool: RepositoryPool
) -> None:
    chooser = Chooser(pool, env)
    package = Package(
        "demo",
        "0.1.0",
        source_type="legacy",
        source_reference="foo",
        source_url="https://foo.bar/simple/",
    )
    package.files = [
        {
            "hash": (
                "sha256:9fa123ad707a5c6c944743bf3e11a0e80d86cb518d3cf25320866ca3ef43e2ad"
            ),
            "filename": "demo-0.1.0.tar.gz",
        }
    ]
    res = chooser.choose_for(package)
    assert res.filename == "demo-0.1.0.tar.gz"
