from __future__ import annotations

import re

from enum import IntEnum
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol
from urllib.parse import urlparse

import pytest
import requests

from requests import codes

from poetry.inspection.lazy_wheel import HTTPRangeRequestNotRespected
from poetry.inspection.lazy_wheel import HTTPRangeRequestUnsupported
from poetry.inspection.lazy_wheel import InvalidWheel
from poetry.inspection.lazy_wheel import LazyWheelUnsupportedError
from poetry.inspection.lazy_wheel import metadata_from_wheel_url
from tests.helpers import http_setup_redirect


if TYPE_CHECKING:
    import httpretty

    from httpretty.core import HTTPrettyRequest
    from pytest_mock import MockerFixture

    from tests.types import FixtureDirGetter
    from tests.types import HTTPPrettyRequestCallbackWrapper
    from tests.types import HTTPrettyRequestCallback
    from tests.types import HTTPrettyResponse

    class RequestCallbackFactory(Protocol):
        def __call__(
            self,
            *,
            accept_ranges: str | None = "bytes",
            negative_offset_error: tuple[int, bytes] | None = None,
            ignore_accept_ranges: bool = False,
        ) -> HTTPrettyRequestCallback: ...

    class AssertMetadataFromWheelUrl(Protocol):
        def __call__(
            self,
            *,
            accept_ranges: str | None = "bytes",
            negative_offset_error: tuple[int, bytes] | None = None,
            expected_requests: int = 3,
            request_callback_wrapper: HTTPPrettyRequestCallbackWrapper | None = None,
            redirect: bool = True,
        ) -> None: ...


class NegativeOffsetFailure(IntEnum):
    # numbers must be negative to avoid conflicts with HTTP status codes
    as_positive = -1  # JFrog Artifactory bug (RTDEV-38572)
    one_more = -2  # JFrog Artifactory bug (one more byte than requested)


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
    negative_offset_failure: NegativeOffsetFailure | None = None,
) -> HTTPrettyResponse:
    status_code = 206
    response_headers["Accept-Ranges"] = "bytes"
    total_length = len(wheel_bytes)
    if rng.startswith("-"):
        # negative offset
        offset = int(rng)
        if negative_offset_failure == NegativeOffsetFailure.as_positive:
            # some servers interpret a negative offset like "-10" as "0-10"
            start = 0
            end = min(-offset, total_length - 1)
            body = wheel_bytes[start : end + 1]
        elif negative_offset_failure == NegativeOffsetFailure.one_more:
            # https://github.com/python-poetry/poetry/issues/9056#issuecomment-1973273721
            offset -= 1  # one more byte
            start = total_length + offset  # negative start of content range possible!
            end = total_length - 1
            body = wheel_bytes[offset:]
            response_headers["Content-Length"] = -offset  # just wrong...
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
        ignore_accept_ranges: bool = False,
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

            negative_offset_failure = None
            if negative_offset_error and rng.startswith("-"):
                if negative_offset_error[0] == codes.requested_range_not_satisfiable:
                    response_headers["Content-Range"] = f"bytes */{len(wheel_bytes)}"
                if negative_offset_error[0] == NegativeOffsetFailure.as_positive:
                    negative_offset_failure = NegativeOffsetFailure.as_positive
                elif negative_offset_error[0] == NegativeOffsetFailure.one_more:
                    negative_offset_failure = NegativeOffsetFailure.one_more
                else:
                    return (
                        negative_offset_error[0],
                        response_headers,
                        negative_offset_error[1],
                    )
            if accept_ranges == "bytes" and rng and not ignore_accept_ranges:
                return build_partial_response(
                    rng,
                    wheel_bytes,
                    response_headers,
                    negative_offset_failure=negative_offset_failure,
                )

            status_code = 200
            body = wheel_bytes

            return status_code, response_headers, body

        return handle_request

    return _factory


@pytest.fixture
def assert_metadata_from_wheel_url(
    http: type[httpretty.httpretty],
    handle_request_factory: RequestCallbackFactory,
) -> AssertMetadataFromWheelUrl:
    def _assertion(
        *,
        accept_ranges: str | None = "bytes",
        negative_offset_error: tuple[int, bytes] | None = None,
        expected_requests: int = 3,
        request_callback_wrapper: HTTPPrettyRequestCallbackWrapper | None = None,
        redirect: bool = False,
    ) -> None:
        latest_requests = http.latest_requests()
        latest_requests.clear()

        domain = (
            f"lazy-wheel-{negative_offset_error[0] if negative_offset_error else 0}.com"
        )
        uri_regex = re.compile(f"^https://{domain}/.*$")
        request_callback = handle_request_factory(
            accept_ranges=accept_ranges, negative_offset_error=negative_offset_error
        )
        if request_callback_wrapper is not None:
            request_callback = request_callback_wrapper(request_callback)

        http.register_uri(http.GET, uri_regex, body=request_callback)
        http.register_uri(http.HEAD, uri_regex, body=request_callback)

        if redirect:
            http_setup_redirect(http, http.GET, http.HEAD)

        url_prefix = "redirect." if redirect else ""
        url = f"https://{url_prefix}{domain}/poetry_core-1.5.0-py3-none-any.whl"

        metadata = metadata_from_wheel_url("poetry-core", url, requests.Session())

        assert metadata["name"] == "poetry-core"
        assert metadata["version"] == "1.5.0"
        assert metadata["author"] == "Sébastien Eustace"
        assert metadata["requires_dist"] == [
            'importlib-metadata (>=1.7.0) ; python_version < "3.8"'
        ]

        assert len(latest_requests) == expected_requests

    return _assertion


@pytest.mark.parametrize(
    "negative_offset_error",
    [
        None,
        (codes.not_found, b"Not found"),  # Nexus
        (codes.method_not_allowed, b"Method not allowed"),
        (codes.requested_range_not_satisfiable, b"Requested range not satisfiable"),
        (codes.internal_server_error, b"Internal server error"),  # GAR
        (codes.not_implemented, b"Unsupported client range"),  # PyPI
        (NegativeOffsetFailure.as_positive, b"handle negative offset as positive"),
        (NegativeOffsetFailure.one_more, b"one more byte than requested"),
    ],
)
def test_metadata_from_wheel_url(
    assert_metadata_from_wheel_url: AssertMetadataFromWheelUrl,
    negative_offset_error: tuple[int, bytes] | None,
) -> None:
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
        if negative_offset_error[0] in {
            codes.requested_range_not_satisfiable,
            NegativeOffsetFailure.as_positive,
            NegativeOffsetFailure.one_more,
        }:
            expected_requests += 1
        else:
            expected_requests += 2

    assert_metadata_from_wheel_url(
        negative_offset_error=negative_offset_error, expected_requests=expected_requests
    )

    # second wheel -> one less request if negative offsets are not supported
    expected_requests = min(expected_requests, 4)
    assert_metadata_from_wheel_url(
        negative_offset_error=negative_offset_error, expected_requests=expected_requests
    )


def test_metadata_from_wheel_url_416_missing_content_range(
    assert_metadata_from_wheel_url: AssertMetadataFromWheelUrl,
) -> None:
    def request_callback_wrapper(
        request_callback: HTTPrettyRequestCallback,
    ) -> HTTPrettyRequestCallback:
        def _wrapped(
            request: HTTPrettyRequest, uri: str, response_headers: dict[str, Any]
        ) -> HTTPrettyResponse:
            status_code, response_headers, body = request_callback(
                request, uri, response_headers
            )
            return (
                status_code,
                {
                    header: response_headers[header]
                    for header in response_headers
                    if header.lower() != "content-range"
                },
                body,
            )

        return _wrapped

    assert_metadata_from_wheel_url(
        negative_offset_error=(
            codes.requested_range_not_satisfiable,
            b"Requested range not satisfiable",
        ),
        expected_requests=5,
        request_callback_wrapper=request_callback_wrapper,
    )


def test_metadata_from_wheel_url_with_redirect(
    assert_metadata_from_wheel_url: AssertMetadataFromWheelUrl,
) -> None:
    assert_metadata_from_wheel_url(
        negative_offset_error=None,
        expected_requests=6,
        redirect=True,
    )


def test_metadata_from_wheel_url_with_redirect_after_500(
    assert_metadata_from_wheel_url: AssertMetadataFromWheelUrl,
) -> None:
    assert_metadata_from_wheel_url(
        negative_offset_error=(codes.internal_server_error, b"Internal server error"),
        expected_requests=10,
        redirect=True,
    )


@pytest.mark.parametrize(
    ("negative_offset_failure", "expected_requests"),
    [
        (None, 1),
        (NegativeOffsetFailure.as_positive, 1),
        (NegativeOffsetFailure.one_more, 2),
    ],
)
def test_metadata_from_wheel_url_smaller_than_initial_chunk_size(
    http: type[httpretty.httpretty],
    handle_request_factory: RequestCallbackFactory,
    negative_offset_failure: NegativeOffsetFailure | None,
    expected_requests: int,
) -> None:
    domain = f"tiny-wheel-{str(negative_offset_failure).casefold()}.com"
    uri_regex = re.compile(f"^https://{domain}/.*$")
    request_callback = handle_request_factory(
        negative_offset_error=(
            (negative_offset_failure, b"") if negative_offset_failure else None
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

    latest_requests = http.latest_requests()
    assert len(latest_requests) == expected_requests


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


def test_metadata_from_wheel_url_range_requests_supported_but_not_respected(
    http: type[httpretty.httpretty],
    handle_request_factory: RequestCallbackFactory,
) -> None:
    domain = "range-requests-not-respected.com"
    uri_regex = re.compile(f"^https://{domain}/.*$")
    request_callback = handle_request_factory(
        negative_offset_error=(codes.method_not_allowed, b"Method not allowed"),
        ignore_accept_ranges=True,
    )
    http.register_uri(http.GET, uri_regex, body=request_callback)
    http.register_uri(http.HEAD, uri_regex, body=request_callback)

    url = f"https://{domain}/poetry_core-1.5.0-py3-none-any.whl"

    with pytest.raises(HTTPRangeRequestNotRespected):
        metadata_from_wheel_url("poetry-core", url, requests.Session())

    latest_requests = http.latest_requests()
    assert len(latest_requests) == 3
    assert latest_requests[0].method == "GET"
    assert latest_requests[1].method == "HEAD"
    assert latest_requests[2].method == "GET"


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


def test_metadata_from_wheel_url_handles_unexpected_errors(
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "poetry.inspection.lazy_wheel.LazyWheelOverHTTP.read_metadata",
        side_effect=RuntimeError(),
    )

    with pytest.raises(LazyWheelUnsupportedError):
        metadata_from_wheel_url(
            "demo-missing-dist-info",
            "https://runtime-error.com/demo_missing_dist_info-0.1.0-py2.py3-none-any.whl",
            requests.Session(),
        )
