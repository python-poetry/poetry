from __future__ import annotations

import threading

from typing import TYPE_CHECKING

from cachecontrol.caches import SeparateBodyFileCache

from poetry.utils.authenticator import AtomicSeparateBodyFileCache


if TYPE_CHECKING:
    from pathlib import Path


KEY = "https://foo.bar/simple/setuptools/"
METADATA = b"cc=4,metadata"
BODY = b"<html><a href='setuptools-84.0.0-py3-none-any.whl'>setuptools</a></html>"


def test_entry_is_not_visible_before_the_body_is_written(tmp_path: Path) -> None:
    cache = AtomicSeparateBodyFileCache(tmp_path)

    cache.set(KEY, METADATA)

    assert cache.get(KEY) is None

    cache.set_body(KEY, BODY)

    assert cache.get(KEY) == METADATA
    body_file = cache.get_body(KEY)
    assert body_file is not None
    assert body_file.read() == BODY


def test_concurrent_lookup_never_sees_an_incomplete_entry(tmp_path: Path) -> None:
    """
    A lookup running while an entry is being published must either miss or see
    the complete entry, never metadata paired with a missing body.
    """
    cache = AtomicSeparateBodyFileCache(tmp_path)
    reader = AtomicSeparateBodyFileCache(tmp_path)

    metadata_published = threading.Event()
    publish_body = threading.Event()

    def writer() -> None:
        cache.set(KEY, METADATA)
        metadata_published.set()
        publish_body.wait(timeout=10)
        cache.set_body(KEY, BODY)

    thread = threading.Thread(target=writer)
    thread.start()
    assert metadata_published.wait(timeout=10)

    assert reader.get(KEY) is None
    assert reader.get_body(KEY) is None

    publish_body.set()
    thread.join(timeout=10)
    assert not thread.is_alive()

    assert reader.get(KEY) == METADATA


def test_upstream_cache_exposes_the_same_window(tmp_path: Path) -> None:
    """
    Guards the premise of this fix: the unmodified cache publishes metadata
    before the body, so a lookup in that window sees an entry with no body.
    """
    cache = SeparateBodyFileCache(tmp_path)
    reader = SeparateBodyFileCache(tmp_path)

    cache.set(KEY, METADATA)

    assert reader.get(KEY) == METADATA
    assert reader.get_body(KEY) is None

    cache.set_body(KEY, BODY)


def test_entry_without_body_is_treated_as_a_miss(tmp_path: Path) -> None:
    """
    Metadata left behind without its body, as happens when a write is
    interrupted, must not be served.
    """
    cache = AtomicSeparateBodyFileCache(tmp_path)
    SeparateBodyFileCache.set(cache, KEY, METADATA)

    assert cache.get(KEY) is None


def test_revalidation_without_a_body_keeps_the_existing_entry(
    tmp_path: Path,
) -> None:
    cache = AtomicSeparateBodyFileCache(tmp_path)

    cache.set(KEY, METADATA)
    cache.set_body(KEY, BODY)
    cache.set(KEY, b"cc=4,revalidated")

    assert cache.get(KEY) == b"cc=4,revalidated"
    body_file = cache.get_body(KEY)
    assert body_file is not None
    assert body_file.read() == BODY


def test_delete_removes_a_pending_entry(tmp_path: Path) -> None:
    cache = AtomicSeparateBodyFileCache(tmp_path)

    cache.set(KEY, METADATA)
    cache.delete(KEY)
    cache.set_body(KEY, BODY)

    assert cache.get(KEY) is None
