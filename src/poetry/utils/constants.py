from __future__ import annotations

import os

from poetry.config.config import int_normalizer


# Name of Poetry's own system project used by `poetry self` commands.
POETRY_SYSTEM_PROJECT_NAME = "poetry-instance"

# Timeout for HTTP requests using the requests library.
REQUESTS_TIMEOUT = 15


def get_requests_timeout() -> int:
    try:
        return int_normalizer(
            os.getenv("POETRY_REQUESTS_TIMEOUT", str(REQUESTS_TIMEOUT))
        )
    except ValueError as e:
        raise ValueError(
            "POETRY_REQUESTS_TIMEOUT must be an integer number of seconds"
        ) from e

RETRY_AFTER_HEADER = "retry-after"

# Server response codes to retry requests on.
STATUS_FORCELIST = [429, 500, 501, 502, 503, 504]
