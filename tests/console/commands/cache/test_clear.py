from __future__ import annotations

from typing import TYPE_CHECKING
from typing import TypeVar

import pytest

from cleo.testers.application_tester import ApplicationTester

from poetry.console.application import Application


if TYPE_CHECKING:
    from pathlib import Path

    from poetry.utils.cache import FileCache

T = TypeVar("T")


@pytest.fixture
def tester() -> ApplicationTester:
    app = Application()

    tester = ApplicationTester(app)
    return tester


@pytest.mark.parametrize("inputs", ["yes", "no"])
def test_cache_clear_all(
    tester: ApplicationTester,
    repository_cache_dir: Path,
    repositories: list[str],
    repository_dirs: list[Path],
    caches: list[FileCache[dict[str, str]]],
    inputs: str,
) -> None:
    exit_code = tester.execute("cache clear --all", inputs=inputs)

    assert exit_code == 0
    assert tester.io.fetch_output() == ""

    if inputs == "yes":
        assert not repository_dirs[0].exists() or not any(repository_dirs[0].iterdir())
        assert not repository_dirs[1].exists() or not any(repository_dirs[1].iterdir())
        assert not caches[0].has("cachy:0.1")
        assert not caches[0].has("cleo:0.2")
        assert not caches[1].has("cachy:0.1")
        assert not caches[1].has("cashy:0.2")
    else:
        assert any((repository_cache_dir / repositories[0]).iterdir())
        assert any((repository_cache_dir / repositories[1]).iterdir())
        assert caches[0].has("cachy:0.1")
        assert caches[0].has("cleo:0.2")
        assert caches[1].has("cachy:0.1")
        assert caches[1].has("cashy:0.2")


@pytest.mark.parametrize("inputs", ["yes", "no"])
def test_cache_clear_all_one_cache(
    tester: ApplicationTester,
    repository_cache_dir: Path,
    repositories: list[str],
    repository_dirs: list[Path],
    caches: list[FileCache[dict[str, str]]],
    inputs: str,
) -> None:
    exit_code = tester.execute(f"cache clear {repositories[0]} --all", inputs=inputs)

    assert exit_code == 0
    assert tester.io.fetch_output() == ""

    if inputs == "yes":
        assert not repository_dirs[0].exists() or not any(repository_dirs[0].iterdir())
        assert not caches[0].has("cachy:0.1")
        assert not caches[0].has("cleo:0.2")
    else:
        assert any((repository_cache_dir / repositories[0]).iterdir())
        assert caches[0].has("cachy:0.1")
        assert caches[0].has("cleo:0.2")

    assert any((repository_cache_dir / repositories[1]).iterdir())
    assert caches[1].has("cachy:0.1")
    assert caches[1].has("cashy:0.2")


def test_cache_clear_all_no_entries(tester: ApplicationTester) -> None:
    exit_code = tester.execute("cache clear --all")

    assert exit_code == 0
    assert tester.io.fetch_output().strip() == "No cache entries"


def test_cache_clear_all_one_cache_no_entries(
    tester: ApplicationTester,
    repository_cache_dir: Path,
    repositories: list[str],
) -> None:
    exit_code = tester.execute(f"cache clear {repositories[0]} --all")

    assert exit_code == 0

    assert tester.io.fetch_output().strip() == f"No cache entries for {repositories[0]}"


@pytest.mark.parametrize("with_repo", [False, True])
def test_cache_clear_missing_option(
    tester: ApplicationTester, repositories: list[str], with_repo: bool
) -> None:
    command = f"cache clear {repositories[0]}" if with_repo else "cache clear"
    exit_code = tester.execute(command)

    assert exit_code == 1
    assert (
        "Add the --all option if you want to clear all cache entries"
        in tester.io.fetch_error()
    )


@pytest.mark.parametrize("inputs", ["yes", "no"])
@pytest.mark.parametrize("package_name", ["cachy", "Cachy"])
def test_cache_clear_pkg(
    tester: ApplicationTester,
    repositories: list[str],
    caches: list[FileCache[dict[str, str]]],
    package_name: str,
    inputs: str,
) -> None:
    exit_code = tester.execute(
        f"cache clear {repositories[1]}:{package_name}:0.1", inputs=inputs
    )

    assert exit_code == 0
    assert tester.io.fetch_output() == ""

    if inputs == "yes":
        assert not caches[1].has("cachy:0.1")
        assert caches[1].has("cashy:0.2")
    else:
        assert caches[1].has("cachy:0.1")
        assert caches[1].has("cashy:0.2")

    assert caches[0].has("cachy:0.1")
