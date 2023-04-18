from __future__ import annotations


# Timeout for HTTP requests using the requests library.
REQUESTS_TIMEOUT = 15

RETRY_AFTER_HEADER = "retry-after"

# Server response codes to retry requests on.
STATUS_FORCELIST = [429, 500, 501, 502, 503, 504]
