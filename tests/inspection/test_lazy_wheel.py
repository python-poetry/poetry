from __future__ import annotations

import re

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import Protocol
from typing import Tuple
from urllib.parse import urlparse

import httpretty
import pytest
import requests

from requests import codes

from poetry.inspection.lazy_wheel import HTTPRangeRequestUnsupported
from poetry.inspection.lazy_wheel import InvalidWheel
from poetry.inspection.lazy_wheel import metadata_from_wheel_url


if TYPE_CHECKING:
    from collections.abc import Callable

    from httpretty.core import HTTPrettyRequest

    from tests.types import FixtureDirGetter

    HTTPrettyResponse = Tuple[int, Dict[str, Any], bytes]  # status code, headers, body
    HTTPrettyRequestCallback = Callable[
        [HTTPrettyRequest, str, Dict[str, Any]], HTTPrettyResponse
    ]

    class RequestCallbackFactory(Protocol):
        def __call__(
            self,
            *,
            accept_ranges: str | None = "bytes",
            negative_offset_error: tuple[int, bytes] | None = None,
        ) -> HTTPrettyRequestCallback: ...


NEGATIVE_OFFSET_AS_POSITIVE = -1


def build_head_response(
    accept_ranges: str | None, content_length: int, response_headers: dict[str, Any]
) -> HTTPrettyResponse:
    response_headers["Content-Length"] = content_length
    if accept_ranges:
        response_headers["Accept-Ranges"] = accept_ranges
    return 200, response_headers, b""


def build_partial_response(
    rng: str,
    wheel_bytes: bytes,
    response_headers: dict[str, Any],
    *,
    negative_offset_as_positive: bool = False,
) -> HTTPrettyResponse:
    status_code = 206
    response_headers["Accept-Ranges"] = "bytes"
    total_length = len(wheel_bytes)
    if rng.startswith("-"):
        # negative offset
        offset = int(rng)
        if negative_offset_as_positive:
            # some servers interpret a negative offset like "-10" as "0-10"
            start = 0
            end = min(-offset, total_length - 1)
            body = wheel_bytes[start : end + 1]
        else:
            start = total_length + offset
            if start < 0:
                # wheel is smaller than initial chunk size
                return 200, response_headers, wheel_bytes
            end = total_length - 1
            body = wheel_bytes[offset:]
    else:
        # range with start and end
        start, end = map(int, rng.split("-"))
        body = wheel_bytes[start : end + 1]
    response_headers["Content-Range"] = f"bytes {start}-{end}/{total_length}"
    return status_code, response_headers, body


@pytest.fixture
def handle_request_factory(fixture_dir: FixtureDirGetter) -> RequestCallbackFactory:
    def _factory(
        *,
        accept_ranges: str | None = "bytes",
        negative_offset_error: tuple[int, bytes] | None = None,
    ) -> HTTPrettyRequestCallback:
        def handle_request(
            request: HTTPrettyRequest, uri: str, response_headers: dict[str, Any]
        ) -> HTTPrettyResponse:
            name = Path(urlparse(uri).path).name

            wheel = Path(__file__).parents[1] / (
                "repositories/fixtures/pypi.org/dists/" + name
            )

            if not wheel.exists():
                wheel = fixture_dir("distributions") / name

                if not wheel.exists():
                    wheel = (
                        fixture_dir("distributions") / "demo-0.1.0-py2.py3-none-any.whl"
                    )

            wheel_bytes = wheel.read_bytes()

            del response_headers["status"]

            if request.method == "HEAD":
                return build_head_response(
                    accept_ranges, len(wheel_bytes), response_headers
                )

            rng = request.headers.get("Range", "=").split("=")[1]

            negative_offset_as_positive = False
            if negative_offset_error and rng.startswith("-"):
                if negative_offset_error[0] == codes.requested_range_not_satisfiable:
                    response_headers["Content-Range"] = f"bytes */{len(wheel_bytes)}"
                if negative_offset_error[0] == NEGATIVE_OFFSET_AS_POSITIVE:
                    negative_offset_as_positive = True
                else:
                    return (
                        negative_offset_error[0],
                        response_headers,
                        negative_offset_error[1],
                    )
            if accept_ranges == "bytes" and rng:
                return build_partial_response(
                    rng,
                    wheel_bytes,
                    response_headers,
                    negative_offset_as_positive=negative_offset_as_positive,
                )

            status_code = 200
            body = wheel_bytes

            return status_code, response_headers, body

        return handle_request

    return _factory


@pytest.mark.parametrize(
    "negative_offset_error",
    [
        None,
        (codes.method_not_allowed, b"Method not allowed"),
        (codes.requested_range_not_satisfiable, b"Requested range not satisfiable"),
        (codes.not_implemented, b"Unsupported client range"),
        (NEGATIVE_OFFSET_AS_POSITIVE, b"handle negative offset as positive"),
    ],
)
def test_metadata_from_wheel_url(
    http: type[httpretty.httpretty],
    handle_request_factory: RequestCallbackFactory,
    negative_offset_error: tuple[int, bytes] | None,
) -> None:
    domain = (
        f"lazy-wheel-{negative_offset_error[0] if negative_offset_error else 0}.com"
    )
    uri_regex = re.compile(f"^https://{domain}/.*$")
    request_callback = handle_request_factory(
        negative_offset_error=negative_offset_error
    )
    http.register_uri(http.GET, uri_regex, body=request_callback)
    http.register_uri(http.HEAD, uri_regex, body=request_callback)

    url = f"https://{domain}/poetry_core-1.5.0-py3-none-any.whl"

    metadata = metadata_from_wheel_url("poetry-core", url, requests.Session())

    assert metadata["name"] == "poetry-core"
    assert metadata["version"] == "1.5.0"
    assert metadata["author"] == "Sébastien Eustace"
    assert metadata["requires_dist"] == [
        'importlib-metadata (>=1.7.0) ; python_version < "3.8"'
    ]

    # negative offsets supported:
    # 1. end of central directory
    # 2. whole central directory
    # 3. METADATA file
    # negative offsets not supported:
    # 1. failed range request
    # 2. HEAD request
    # 3.-5. see negative offsets 1.-3.
    expected_requests = 3
    if negative_offset_error:
        if negative_offset_error[0] in (
            codes.requested_range_not_satisfiable,
            NEGATIVE_OFFSET_AS_POSITIVE,
        ):
            expected_requests += 1
        else:
            expected_requests += 2
    latest_requests = http.latest_requests()
    assert len(latest_requests) == expected_requests

    # second wheel -> one less request if negative offsets are not supported
    latest_requests.clear()
    metadata_from_wheel_url("poetry-core", url, requests.Session())
    expected_requests = min(expected_requests, 4)
    latest_requests = httpretty.latest_requests()
    assert len(latest_requests) == expected_requests


@pytest.mark.parametrize("negative_offset_as_positive", [False, True])
def test_metadata_from_wheel_url_smaller_than_initial_chunk_size(
    http: type[httpretty.httpretty],
    handle_request_factory: RequestCallbackFactory,
    negative_offset_as_positive: bool,
) -> None:
    domain = f"tiny-wheel-{str(negative_offset_as_positive).casefold()}.com"
    uri_regex = re.compile(f"^https://{domain}/.*$")
    request_callback = handle_request_factory(
        negative_offset_error=(
            (NEGATIVE_OFFSET_AS_POSITIVE, b"") if negative_offset_as_positive else None
        )
    )
    http.register_uri(http.GET, uri_regex, body=request_callback)
    http.register_uri(http.HEAD, uri_regex, body=request_callback)

    url = f"https://{domain}/zipp-3.5.0-py3-none-any.whl"

    metadata = metadata_from_wheel_url("zipp", url, requests.Session())

    assert metadata["name"] == "zipp"
    assert metadata["version"] == "3.5.0"
    assert metadata["author"] == "Jason R. Coombs"
    assert len(metadata["requires_dist"]) == 12

    # only one request because server gives a normal response with the entire wheel
    # except for when server interprets negative offset as positive
    latest_requests = http.latest_requests()
    assert len(latest_requests) == 1


@pytest.mark.parametrize("accept_ranges", [None, "none"])
def test_metadata_from_wheel_url_range_requests_not_supported_one_request(
    http: type[httpretty.httpretty],
    handle_request_factory: RequestCallbackFactory,
    accept_ranges: str | None,
) -> None:
    domain = "no-range-requests.com"
    uri_regex = re.compile(f"^https://{domain}/.*$")
    request_callback = handle_request_factory(accept_ranges=accept_ranges)
    http.register_uri(http.GET, uri_regex, body=request_callback)
    http.register_uri(http.HEAD, uri_regex, body=request_callback)

    url = f"https://{domain}/poetry_core-1.5.0-py3-none-any.whl"

    with pytest.raises(HTTPRangeRequestUnsupported):
        metadata_from_wheel_url("poetry-core", url, requests.Session())

    latest_requests = http.latest_requests()
    assert len(latest_requests) == 1
    assert latest_requests[0].method == "GET"


@pytest.mark.parametrize(
    "negative_offset_error",
    [
        (codes.method_not_allowed, b"Method not allowed"),
        (codes.not_implemented, b"Unsupported client range"),
    ],
)
def test_metadata_from_wheel_url_range_requests_not_supported_two_requests(
    http: type[httpretty.httpretty],
    handle_request_factory: RequestCallbackFactory,
    negative_offset_error: tuple[int, bytes],
) -> None:
    domain = f"no-negative-offsets-{negative_offset_error[0]}.com"
    uri_regex = re.compile(f"^https://{domain}/.*$")
    request_callback = handle_request_factory(
        accept_ranges=None, negative_offset_error=negative_offset_error
    )
    http.register_uri(http.GET, uri_regex, body=request_callback)
    http.register_uri(http.HEAD, uri_regex, body=request_callback)

    url = f"https://{domain}/poetry_core-1.5.0-py3-none-any.whl"

    with pytest.raises(HTTPRangeRequestUnsupported):
        metadata_from_wheel_url("poetry-core", url, requests.Session())

    latest_requests = http.latest_requests()
    assert len(latest_requests) == 2
    assert latest_requests[0].method == "GET"
    assert latest_requests[1].method == "HEAD"


def test_metadata_from_wheel_url_invalid_wheel(
    http: type[httpretty.httpretty],
    handle_request_factory: RequestCallbackFactory,
) -> None:
    domain = "invalid-wheel.com"
    uri_regex = re.compile(f"^https://{domain}/.*$")
    request_callback = handle_request_factory()
    http.register_uri(http.GET, uri_regex, body=request_callback)
    http.register_uri(http.HEAD, uri_regex, body=request_callback)

    url = f"https://{domain}/demo_missing_dist_info-0.1.0-py2.py3-none-any.whl"

    with pytest.raises(InvalidWheel):
        metadata_from_wheel_url("demo-missing-dist-info", url, requests.Session())

    latest_requests = http.latest_requests()
    assert len(latest_requests) == 1
    assert latest_requests[0].method == "GET"
