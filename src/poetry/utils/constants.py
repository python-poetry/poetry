from __future__ import annotations

import os

from poetry.exceptions import PoetryError


# Name of Poetry's own system project used by `poetry self` commands.
POETRY_SYSTEM_PROJECT_NAME = "poetry-instance"

# Default timeout for HTTP requests using the requests library.
DEFAULT_REQUESTS_TIMEOUT = 15


def get_requests_timeout() -> int:
    """
    Returns the timeout for HTTP requests using the requests library.

    The value is read lazily so that a malformed ``POETRY_REQUESTS_TIMEOUT``
    only fails the commands that actually perform HTTP requests instead of
    breaking every command at import time.
    """
    value = os.getenv("POETRY_REQUESTS_TIMEOUT")
    if value is None:
        return DEFAULT_REQUESTS_TIMEOUT

    try:
        return int(value)
    except ValueError:
        raise PoetryError(
            f"POETRY_REQUESTS_TIMEOUT must be an integer, got {value!r}"
        ) from None


RETRY_AFTER_HEADER = "retry-after"

# Server response codes to retry requests on.
STATUS_FORCELIST = [429, 500, 501, 502, 503, 504]
