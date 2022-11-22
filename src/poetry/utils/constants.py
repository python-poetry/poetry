from __future__ import annotations


# Timeout for HTTP requests using the requests library.
REQUESTS_TIMEOUT = 15

# Server response codes to retry requests on.
STATUS_FORCELIST = [500, 501, 502, 503, 504]
