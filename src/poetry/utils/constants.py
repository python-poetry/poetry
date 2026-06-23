from __future__ import annotations

import os


# Name of Poetry's own system project used by `poetry self` commands.
POETRY_SYSTEM_PROJECT_NAME = "poetry-instance"

# Timeout for HTTP requests using the requests library.
REQUESTS_TIMEOUT = int(os.getenv("POETRY_REQUESTS_TIMEOUT", 15))

RETRY_AFTER_HEADER = "retry-after"

# Server response codes to retry requests on.
STATUS_FORCELIST = [429, 500, 501, 502, 503, 504]

# Force the use of cached http responses even if they are stale.
# This is useful for performance analyses to rule out a source of uncertainty.
FORCE_HTTP_CACHE = os.getenv("POETRY_FORCE_HTTP_CACHE", "").lower() in ("true", "1")
