from __future__ import annotations

import contextlib
import shutil

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from zipfile import ZipFile

import pytest

from packaging.metadata import parse_email
from poetry.core.packages.utils.link import Link

from poetry.inspection.info import PackageInfoError
from poetry.inspection.lazy_wheel import HTTPRangeRequestUnsupportedError
from poetry.repositories.http_repository import HTTPRepository
from poetry.utils.helpers import HTTPRangeRequestSupportedError


if TYPE_CHECKING:
    from packaging.utils import NormalizedName
    from poetry.core.constraints.version import Version
    from pytest_mock import MockerFixture


class MockRepository(HTTPRepository):
    DIST_FIXTURES = Path(__file__).parent / "fixtures" / "pypi.org" / "dists"

    def __init__(self, lazy_wheel: bool = True, disable_cache: bool = False) -> None:
        super().__init__("foo", "https://foo.com", disable_cache=disable_cache)
        self._lazy_wheel = lazy_wheel

    def _get_release_info(
        self, name: NormalizedName, version: Version
    ) -> dict[str, Any]:
        raise NotImplementedError


@pytest.mark.parametrize("lazy_wheel", [False, True])
@pytest.mark.parametrize("supports_range_requests", [None, False, True])
def test_get_info_from_wheel(
    mocker: MockerFixture, lazy_wheel: bool, supports_range_requests: bool | None
) -> None:
    filename = "poetry_core-1.5.0-py3-none-any.whl"
    filepath = MockRepository.DIST_FIXTURES / filename
    with ZipFile(filepath) as zf:
        metadata, _ = parse_email(zf.read("poetry_core-1.5.0.dist-info/METADATA"))

    mock_metadata_from_wheel_url = mocker.patch(
        "poetry.repositories.http_repository.metadata_from_wheel_url",
        return_value=metadata,
    )
    mock_download = mocker.patch(
        "poetry.repositories.http_repository.download_file",
        side_effect=lambda _, dest, *args, **kwargs: shutil.copy(filepath, dest),
    )

    domain = "foo.com"
    url = f"https://{domain}/{filename}"
    repo = MockRepository(lazy_wheel)
    assert not repo._supports_range_requests
    if lazy_wheel and supports_range_requests is not None:
        repo._supports_range_requests[domain] = supports_range_requests

    info = repo._get_info_from_wheel(Link(url))
    assert info.name == "poetry-core"
    assert info.version == "1.5.0"
    assert info.requires_dist == [
        'importlib-metadata (>=1.7.0) ; python_version < "3.8"'
    ]

    if lazy_wheel and supports_range_requests is not False:
        mock_metadata_from_wheel_url.assert_called_once_with(
            filename, url, repo.session
        )
        mock_download.assert_not_called()
        assert repo._supports_range_requests[domain] is True
    else:
        mock_metadata_from_wheel_url.assert_not_called()
        mock_download.assert_called_once_with(
            url,
            mocker.ANY,
            session=repo.session,
            raise_accepts_ranges=lazy_wheel,
            max_retries=0,
        )
        if lazy_wheel:
            assert repo._supports_range_requests[domain] is False
        else:
            assert domain not in repo._supports_range_requests


def test_get_info_from_wheel_state_sequence(mocker: MockerFixture) -> None:
    """
    1. We know nothing:
       Try range requests, which are not supported and fall back to complete download.
    2. Range requests were not supported so far:
       We do not try range requests again.
    3. Range requests were still not supported so far:
       We do not try range requests again, but we notice that the response header
       contains "Accept-Ranges: bytes", so range requests are at least supported
       for some files, which means we want to try again.
    4. Range requests are supported for some files:
       We try range requests (success).
    5. Range requests are supported for some files:
       We try range requests (failure), but do not forget that range requests are
       supported for some files.
    6. Range requests are supported for some files:
       We try range requests (success).
    """
    mock_metadata_from_wheel_url = mocker.patch(
        "poetry.repositories.http_repository.metadata_from_wheel_url"
    )
    mock_download = mocker.patch("poetry.repositories.http_repository.download_file")

    filename = "poetry_core-1.5.0-py3-none-any.whl"
    domain = "foo.com"
    link = Link(f"https://{domain}/{filename}")
    repo = MockRepository()

    # 1. range request and download
    mock_metadata_from_wheel_url.side_effect = HTTPRangeRequestUnsupportedError

    with contextlib.suppress(PackageInfoError):
        repo._get_info_from_wheel(link)

    assert mock_metadata_from_wheel_url.call_count == 1
    assert mock_download.call_count == 1
    assert mock_download.call_args[1]["raise_accepts_ranges"] is False

    # 2. only download
    with contextlib.suppress(PackageInfoError):
        repo._get_info_from_wheel(link)

    assert mock_metadata_from_wheel_url.call_count == 1
    assert mock_download.call_count == 2
    assert mock_download.call_args[1]["raise_accepts_ranges"] is True

    # 3. download and range request
    mock_metadata_from_wheel_url.side_effect = None
    mock_download.side_effect = HTTPRangeRequestSupportedError

    with contextlib.suppress(PackageInfoError):
        repo._get_info_from_wheel(link)

    assert mock_metadata_from_wheel_url.call_count == 2
    assert mock_download.call_count == 3
    assert mock_download.call_args[1]["raise_accepts_ranges"] is True

    # 4. only range request
    with contextlib.suppress(PackageInfoError):
        repo._get_info_from_wheel(link)

    assert mock_metadata_from_wheel_url.call_count == 3
    assert mock_download.call_count == 3

    # 5. range request and download
    mock_metadata_from_wheel_url.side_effect = HTTPRangeRequestUnsupportedError
    mock_download.side_effect = None

    with contextlib.suppress(PackageInfoError):
        repo._get_info_from_wheel(link)

    assert mock_metadata_from_wheel_url.call_count == 4
    assert mock_download.call_count == 4
    assert mock_download.call_args[1]["raise_accepts_ranges"] is False

    # 6. only range request
    mock_metadata_from_wheel_url.side_effect = None

    with contextlib.suppress(PackageInfoError):
        repo._get_info_from_wheel(link)

    assert mock_metadata_from_wheel_url.call_count == 5
    assert mock_download.call_count == 4


@pytest.mark.parametrize(
    "mock_hashes",
    [
        None,
        {"sha256": "e216b70f013c47b82a72540d34347632c5bfe59fd54f5fe5d51f6a68b19aaf84"},
        {"md5": "be7589b4902793e66d7d979bd8581591"},
    ],
)
def test_calculate_sha256(
    mocker: MockerFixture, mock_hashes: dict[str, Any] | None
) -> None:
    filename = "poetry_core-1.5.0-py3-none-any.whl"
    filepath = MockRepository.DIST_FIXTURES / filename
    mock_download = mocker.patch(
        "poetry.repositories.http_repository.download_file",
        side_effect=lambda _, dest, *args, **kwargs: shutil.copy(filepath, dest),
    )
    domain = "foo.com"
    link = Link(f"https://{domain}/{filename}", hashes=mock_hashes)
    repo = MockRepository()

    calculated_hash = repo.calculate_sha256(link)

    assert mock_download.call_count == 1
    assert (
        calculated_hash
        == "sha256:e216b70f013c47b82a72540d34347632c5bfe59fd54f5fe5d51f6a68b19aaf84"
    )


def test_calculate_sha256_defaults_to_sha256_on_md5_errors(
    mocker: MockerFixture,
) -> None:
    raised_value_error = False

    def mock_hashlib_md5_error() -> None:
        nonlocal raised_value_error
        raised_value_error = True
        raise ValueError(
            "[digital envelope routines: EVP_DigestInit_ex] disabled for FIPS"
        )

    filename = "poetry_core-1.5.0-py3-none-any.whl"
    filepath = MockRepository.DIST_FIXTURES / filename
    mock_download = mocker.patch(
        "poetry.repositories.http_repository.download_file",
        side_effect=lambda _, dest, *args, **kwargs: shutil.copy(filepath, dest),
    )
    mock_hashlib_md5 = mocker.patch("hashlib.md5", side_effect=mock_hashlib_md5_error)

    domain = "foo.com"
    link = Link(
        f"https://{domain}/{filename}",
        hashes={"md5": "be7589b4902793e66d7d979bd8581591"},
    )
    repo = MockRepository()

    calculated_hash = repo.calculate_sha256(link)

    assert raised_value_error
    assert mock_download.call_count == 1
    assert mock_hashlib_md5.call_count == 1
    assert (
        calculated_hash
        == "sha256:e216b70f013c47b82a72540d34347632c5bfe59fd54f5fe5d51f6a68b19aaf84"
    )


@pytest.mark.parametrize("disable_cache", [False, True])
def test_get_page_respects_disable_cache(disable_cache: bool) -> None:
    """Regression test for issue #10584.

    ``poetry update --no-cache`` must bypass the in-memory LRU page cache so
    that a distribution whose file list changes between invocations is always
    fetched fresh.  Without the fix, ``get_page`` was unconditionally backed by
    an ``lru_cache`` instance attribute set at construction time, meaning that
    even with ``disable_cache=True`` the stale page was returned on repeated
    calls within the same process, causing the lockfile to diverge from what a
    non-cached run would produce.

    The test uses two sentinel page objects to represent the state of a
    hypothetical package index before and after a distribution update.  No
    network calls or timing assumptions are involved.
    """

    class _PageV1:
        """Represents the initial state of the package index page."""

    class _PageV2:
        """Represents the updated state of the package index page (new distribution)."""

    page_v1 = _PageV1()
    page_v2 = _PageV2()
    pages = [page_v1, page_v2]
    call_log: list[str] = []

    # Subclass with a _get_page that returns different pages on each call,
    # simulating a remote index that changes between invocations (e.g. a new
    # wheel file is published between two ``poetry update`` runs).
    class TrackingRepository(HTTPRepository):
        def _get_page(self, name: NormalizedName) -> Any:  # type: ignore[override]
            call_log.append(str(name))
            return pages[len(call_log) - 1]

        def _get_release_info(
            self, name: NormalizedName, version: Version
        ) -> dict[str, Any]:
            raise NotImplementedError

    repo = TrackingRepository(
        "test-repo", "https://example.invalid", disable_cache=disable_cache
    )

    first = repo.get_page("mypackage")  # type: ignore[arg-type]
    assert first is page_v1
    assert len(call_log) == 1

    # Simulate the remote distribution changing: the next raw fetch would
    # return page_v2.  With --no-cache the lockfile should reflect this new
    # state; without --no-cache the cached page should be served instead.
    second = repo.get_page("mypackage")  # type: ignore[arg-type]

    if disable_cache:
        # --no-cache path: _get_page is called again, returning updated data.
        # The lockfile built from this data will be consistent with the current
        # state of the index rather than a stale snapshot.
        assert second is page_v2, (
            "With disable_cache=True, get_page must bypass the LRU cache and "
            "return fresh data on every call (issue #10584)"
        )
        assert len(call_log) == 2
    else:
        # Normal (cached) path: _get_page is only called once; the LRU cache
        # serves the first result on all subsequent calls for the same name.
        assert second is page_v1, (
            "With disable_cache=False, get_page must return the cached page"
        )
        assert len(call_log) == 1


def test_no_cache_matches_cold_cache_after_distribution_change() -> None:
    """Issue #10584: ``--no-cache`` must be equivalent to a cold-cache run.

    The key question this test answers: would it *actually fail* on the old
    (unfixed) code?  Yes — because it uses the **same** repository instance
    for both the seeding call and the post-change call, so any in-memory LRU
    state accumulated during the seed directly contaminates the second lookup.

    Scenario
    --------
    A single ``disable_cache=True`` repository object is used across two
    sequential calls — the kind of reuse that occurs when ``_find_packages``
    and ``_get_release_info`` both call ``get_page`` for the same package
    within one resolve cycle, or when the repository object is held across
    multiple solver iterations in library/SDK usage.

    Timeline
    ~~~~~~~~
    1. Seed call  – ``get_page("pkg")`` is invoked once on the
       ``disable_cache=True`` instance while the index is at state A
       (``page_v1``).  On the *old* code this silently warmed the LRU cache
       because the cache was always active regardless of the flag.
    2. Index changes to state B (``page_v2``).
    3. Second call – ``get_page("pkg")`` is invoked again on the **same**
       instance.
       * Old code: LRU hit → returns stale ``page_v1``.   ❌
       * New code: flag checked at call time → returns fresh ``page_v2``. ✓
    4. Cold-cache check – a brand-new ``disable_cache=False`` instance
       (empty LRU, no prior state) fetches once and also returns ``page_v2``.

    The invariant ``second_no_cache_result is cold_result`` would be FALSE on
    the old code (``page_v1 is page_v2`` → False) and TRUE on the fixed code.
    No network calls or timing assumptions are involved.
    """

    page_v1 = object()  # index state *before* the distribution change
    page_v2 = object()  # index state *after*  the distribution change

    # Mutable dict acting as the shared "remote" state.  Reassigning
    # remote["page"] simulates the package index being updated.
    remote: dict[str, object] = {"page": page_v1}

    class StableRepository(HTTPRepository):
        """Always returns whatever the remote dict currently holds."""

        def _get_page(self, name: NormalizedName) -> Any:  # type: ignore[override]
            return remote["page"]

        def _get_release_info(
            self, name: NormalizedName, version: Version
        ) -> dict[str, Any]:
            raise NotImplementedError

    pkg = "mypackage"  # type: ignore[assignment]

    # ── Step 1: seed call on the --no-cache instance ────────────────────────
    # This is the call that silently warms the LRU cache on the old code.
    # Using the same instance (not a fresh one) is what makes the test
    # falsifiable: the stale LRU state is carried into step 3.
    no_cache_repo = StableRepository(
        "test-no-cache", "https://example.invalid", disable_cache=True
    )
    seed_result = no_cache_repo.get_page(pkg)
    assert seed_result is page_v1  # both old and new code return this

    # ── Step 2: index changes ───────────────────────────────────────────────
    remote["page"] = page_v2

    # ── Step 3: second call on the *same* no-cache instance ─────────────────
    # Old code: LRU hit → stale page_v1 returned (bug).
    # New code: _disable_cache checked → _get_page called → page_v2 returned.
    second_no_cache_result = no_cache_repo.get_page(pkg)

    # ── Step 4: cold-cache check ─────────────────────────────────────────────
    # A brand-new instance has an empty LRU so it always calls _get_page once
    # and returns the current remote state.  This is the ground truth.
    cold_repo = StableRepository(
        "test-cold", "https://example.invalid", disable_cache=False
    )
    cold_result = cold_repo.get_page(pkg)

    # ── Step 5: assert the invariant ────────────────────────────────────────
    assert cold_result is page_v2  # sanity: cold instance sees current state

    assert second_no_cache_result is page_v2, (
        "disable_cache=True must bypass the LRU cache on every call; "
        "the seed call must not contaminate subsequent lookups (issue #10584)"
    )
    assert second_no_cache_result is cold_result, (
        "poetry update --no-cache must produce the same page data as a "
        "brand-new cold-cache run; any divergence means the lockfile "
        "would differ between the two invocations (issue #10584)"
    )


def test_no_cache_full_resolution_both_cache_layers_bypassed(tmp_path: Path) -> None:
    """Combined regression test for issue #10584.

    The previous tests verify that ``get_page`` respects ``disable_cache``,
    but they operate at the page layer in isolation.  This test exercises the
    full ``get_release_info → _get_release_info → get_page`` call chain so that
    *both* cache layers — the in-memory page LRU and the disk-based
    release-info cache — are exercised together.

    The hybrid stale/fresh failure mode being guarded against
    -------------------------------------------------------
    With ``disable_cache=True``:
    * Layer 2 (disk release-info cache) is correctly bypassed:
      ``_get_release_info`` is called on every invocation.           ✓
    * Layer 1 (in-memory page LRU) was NOT bypassed on old code:
      ``_get_release_info`` called ``get_page`` which returned the
      stale LRU-cached page, so the metadata was assembled from wrong
      file links even though the disk cache was correctly skipped.   ✗

    Result: a lockfile that diverges from what a cold-cache run would
    produce — it contains the right package version but wrong hashes /
    wrong dependency set (built from the stale page's distribution links).

    Two scenarios
    -------------
    Scenario A – within-session reuse (``disable_cache=True``, same instance)
        The same repository instance is called twice; the distribution changes
        between calls.  The second call must assemble metadata from the updated
        page, not from the stale LRU entry left by the first call.
        *This scenario fails on the old (unfixed) code.*

    Scenario B – cross-run disk-cache bypass (``disable_cache=False → True``)
        A normal cached run populates the on-disk release-info cache with v1
        data.  A subsequent ``--no-cache`` run using a fresh instance that
        shares the same cache directory must return v2 data.  Because the new
        instance has an empty LRU, this scenario passes on both old and new
        code; it is included to confirm the full combined invariant holds.

    No network calls or timing assumptions are involved.
    """
    from packaging.utils import canonicalize_name
    from poetry.core.constraints.version import Version
    from poetry.inspection.info import PackageInfo
    from poetry.repositories.cached_repository import CachedRepository
    from poetry.utils.cache import FileCache

    page_v1 = object()  # remote state before distribution update
    page_v2 = object()  # remote state after  distribution update

    # Distribution state A: initial wheel, no extra dependencies.
    release_info_v1 = PackageInfo(
        name="mylib",
        version="1.0",
        summary="",
        requires_dist=[],
        requires_python=">=3.9",
        files=[{"file": "mylib-1.0-py3-none-any.whl", "hash": "sha256:aaaa"}],
        cache_version=str(CachedRepository.CACHE_VERSION),
    )
    # Distribution state B: new wheel with an added dependency — both the
    # file list *and* the metadata differ from v1.
    release_info_v2 = PackageInfo(
        name="mylib",
        version="1.0",
        summary="",
        requires_dist=["requests>=2"],
        requires_python=">=3.10",
        files=[{"file": "mylib-1.0-cp311-none-any.whl", "hash": "sha256:bbbb"}],
        cache_version=str(CachedRepository.CACHE_VERSION),
    )

    # Shared mutable "remote": changing this simulates the index being updated.
    remote: dict[str, object] = {"page": page_v1}

    class FullResolutionRepository(HTTPRepository):
        """Mirrors ``LegacyRepository._get_release_info``.

        The key structural property: ``_get_release_info`` routes through the
        *public* ``get_page`` method (not ``_get_page`` directly) so that
        both cache layers interact exactly as they do in production code.
        The page returned by ``get_page`` determines which release info is
        assembled, reproducing the real coupling between the two layers.
        """

        def _get_page(self, name: NormalizedName) -> Any:  # type: ignore[override]
            return remote["page"]

        def _get_release_info(
            self, name: NormalizedName, version: Version
        ) -> dict[str, Any]:
            page = self.get_page(name)  # type: ignore[arg-type]
            # asdict() produces a fresh dict each call, so PackageInfo.load's
            # pop("_cache_version") never corrupts the source objects.
            return (release_info_v1 if page is page_v1 else release_info_v2).asdict()

    pkg = canonicalize_name("mylib")
    ver = Version.parse("1.0")

    # ─────────────────────────────────────────────────────────────────────
    # Scenario A: within-session reuse — the canonical failure mode
    # ─────────────────────────────────────────────────────────────────────
    no_cache_repo = FullResolutionRepository(
        "test-nc", "https://example.invalid", disable_cache=True
    )
    no_cache_repo._release_cache = FileCache(path=tmp_path / "nc_cache")

    # First call: seeds the page LRU with page_v1 on old code.
    # (On new code, the LRU is never written because get_page bypasses it.)
    result_a1 = no_cache_repo.get_release_info(pkg, ver)
    assert result_a1.files == release_info_v1.files  # sanity: v1 state

    # Distribution changes: new wheel, new dependency.
    remote["page"] = page_v2

    # Second call on the *same* instance.
    # Old code: page LRU hit → page_v1 → _get_release_info returns v1.asdict()
    #           → get_release_info returns release_info_v1.  ✗
    # New code: page LRU bypassed → page_v2 → release_info_v2.  ✓
    result_a2 = no_cache_repo.get_release_info(pkg, ver)

    assert result_a2.files == release_info_v2.files, (
        "Scenario A: the page LRU must be bypassed on every call when "
        "disable_cache=True; after the distribution changes, get_release_info "
        "must assemble metadata from the updated page links, not from stale "
        "LRU-cached links (hybrid stale/fresh failure, issue #10584)"
    )
    assert result_a2.requires_dist == release_info_v2.requires_dist, (
        "Scenario A: the assembled dependency set must also reflect the "
        "updated page, not the stale LRU snapshot"
    )

    # ─────────────────────────────────────────────────────────────────────
    # Scenario B: cross-run disk-cache bypass
    # ─────────────────────────────────────────────────────────────────────
    remote["page"] = page_v1  # reset for the warm run
    shared_cache = tmp_path / "shared_cache"

    # Warm run: populate the on-disk release-info cache with v1 data.
    cached_repo = FullResolutionRepository(
        "test-cached", "https://example.invalid", disable_cache=False
    )
    cached_repo._release_cache = FileCache(path=shared_cache)
    warm_result = cached_repo.get_release_info(pkg, ver)
    assert warm_result.files == release_info_v1.files  # sanity

    # Distribution changes again.
    remote["page"] = page_v2

    # Sanity-check: the cached repo still serves stale data from disk.
    stale_check = cached_repo.get_release_info(pkg, ver)
    assert stale_check.files == release_info_v1.files, (
        "Scenario B pre-condition: disk cache must still serve stale v1 data "
        "after the distribution changes"
    )

    # --no-cache run: fresh instance pointing at the same on-disk cache
    # (the shared cache directory contains the stale v1 entry written above).
    no_cache_repo_b = FullResolutionRepository(
        "test-nc-b", "https://example.invalid", disable_cache=True
    )
    no_cache_repo_b._release_cache = FileCache(path=shared_cache)
    result_b = no_cache_repo_b.get_release_info(pkg, ver)

    assert result_b.files == release_info_v2.files, (
        "Scenario B: disable_cache=True must bypass the disk release-info "
        "cache; even when the shared cache holds stale v1 data, the --no-cache "
        "run must return the updated v2 distribution (issue #10584)"
    )

    # ─────────────────────────────────────────────────────────────────────
    # Combined invariant: both --no-cache results equal a cold-cache run
    # ─────────────────────────────────────────────────────────────────────
    cold_repo = FullResolutionRepository(
        "test-cold", "https://example.invalid", disable_cache=False
    )
    cold_repo._release_cache = FileCache(path=tmp_path / "cold_cache")  # empty
    cold_result = cold_repo.get_release_info(pkg, ver)
    assert cold_result.files == release_info_v2.files  # sanity

    assert result_a2.files == cold_result.files, (
        "Combined invariant (Scenario A): --no-cache on a warm instance must "
        "match a brand-new cold-cache run — both layers bypassed together"
    )
    assert result_a2.requires_dist == cold_result.requires_dist
    assert result_b.files == cold_result.files, (
        "Combined invariant (Scenario B): --no-cache with stale disk cache "
        "must also match a cold-cache run"
    )
