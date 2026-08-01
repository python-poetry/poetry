from __future__ import annotations

import os

from poetry.config.config import int_normalizer


# Name of Poetry's own system project used by `poetry self` commands.
POETRY_SYSTEM_PROJECT_NAME = "poetry-instance"

# Timeout for HTTP requests using the requests library.
REQUESTS_TIMEOUT = 15
_REQUESTS_TIMEOUT_CACHE_UNSET = object()
_REQUESTS_TIMEOUT_CACHE_INVALID = object()
_requests_timeout_cache: int | object = _REQUESTS_TIMEOUT_CACHE_UNSET


def get_requests_timeout() -> int:
    global _requests_timeout_cache

    if _requests_timeout_cache is _REQUESTS_TIMEOUT_CACHE_UNSET:
        try:
            _requests_timeout_cache = int_normalizer(
                os.getenv("POETRY_REQUESTS_TIMEOUT", str(REQUESTS_TIMEOUT))
            )
        except ValueError:
            _requests_timeout_cache = _REQUESTS_TIMEOUT_CACHE_INVALID

    if _requests_timeout_cache is _REQUESTS_TIMEOUT_CACHE_INVALID:
        raise ValueError("POETRY_REQUESTS_TIMEOUT must be an integer number of seconds")

    assert isinstance(_requests_timeout_cache, int)
    return _requests_timeout_cache


def _reset_requests_timeout_cache() -> None:
    global _requests_timeout_cache

    _requests_timeout_cache = _REQUESTS_TIMEOUT_CACHE_UNSET


RETRY_AFTER_HEADER = "retry-after"

# Server response codes to retry requests on.
STATUS_FORCELIST = [429, 500, 501, 502, 503, 504]
