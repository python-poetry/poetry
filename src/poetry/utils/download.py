from __future__ import annotations

from contextlib import suppress
from functools import cached_property
from typing import TYPE_CHECKING

from requests.exceptions import ChunkedEncodingError
from requests.exceptions import ConnectionError
from requests.utils import atomic_open

from poetry.utils.authenticator import Authenticator
from poetry.utils.authenticator import get_default_authenticator
from poetry.utils.constants import REQUESTS_TIMEOUT
from poetry.utils.helpers import HTTPRangeRequestSupportedError


if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from requests import Response
    from requests import Session


def download_file(
    url: str,
    dest: Path,
    *,
    session: Authenticator | Session | None = None,
    chunk_size: int = 1024,
    raise_accepts_ranges: bool = False,
    max_retries: int = 0,
) -> None:
    from poetry.puzzle.provider import Indicator

    downloader = Downloader(url, dest, session, max_retries=max_retries)

    if raise_accepts_ranges and downloader.accepts_ranges:
        raise HTTPRangeRequestSupportedError(f"URL {url} supports range requests.")

    set_indicator = False
    with Indicator.context() as update_context:
        update_context(f"Downloading {url}")

        total_size = downloader.total_size
        if total_size > 0:
            fetched_size = 0
            last_percent = 0

            # if less than 1MB, we simply show that we're downloading
            # but skip the updating
            set_indicator = total_size > 1024 * 1024

        for fetched_size in downloader.download_with_progress(chunk_size):
            if set_indicator:
                percent = (fetched_size * 100) // total_size
                if percent > last_percent:
                    last_percent = percent
                    update_context(f"Downloading {url} {percent:3}%")


class Downloader:
    def __init__(
        self,
        url: str,
        dest: Path,
        session: Authenticator | Session | None = None,
        max_retries: int = 0,
    ):
        self._dest = dest
        self._max_retries = max_retries
        if session is None:
            session = get_default_authenticator()
        self._session = session
        self._url = url
        self._response = self._get()

    @cached_property
    def accepts_ranges(self) -> bool:
        return self._response.headers.get("Accept-Ranges") == "bytes"

    @cached_property
    def total_size(self) -> int:
        total_size = 0
        if "Content-Length" in self._response.headers:
            with suppress(ValueError):
                total_size = int(self._response.headers["Content-Length"])
        return total_size

    def _get(self, start: int = 0) -> Response:
        headers = {"Accept-Encoding": "Identity"}
        if start > 0:
            headers["Range"] = f"bytes={start}-"

        response = self._session.get(
            self._url, stream=True, headers=headers, timeout=REQUESTS_TIMEOUT
        )
        try:
            response.raise_for_status()
            return response
        except BaseException:
            response.close()
            raise

    def _iter_content_with_resume(self, chunk_size: int) -> Iterator[bytes]:
        fetched_size = 0
        retries = 0
        while True:
            try:
                with self._response:
                    for chunk in self._response.iter_content(chunk_size=chunk_size):
                        yield chunk
                        fetched_size += len(chunk)
            except (ChunkedEncodingError, ConnectionError):
                if (
                    retries < self._max_retries
                    and self.accepts_ranges
                    and fetched_size > 0
                ):
                    # only retry if server supports byte ranges
                    # and we have fetched at least one chunk
                    # otherwise, we should just fail
                    retries += 1
                    self._response = self._get(fetched_size)
                    continue
                raise
            else:
                break

    def download_with_progress(self, chunk_size: int = 1024) -> Iterator[int]:
        fetched_size = 0
        with atomic_open(self._dest) as f:
            for chunk in self._iter_content_with_resume(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    fetched_size += len(chunk)
                    yield fetched_size
