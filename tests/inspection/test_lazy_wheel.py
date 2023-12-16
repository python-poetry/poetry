from __future__ import annotations

import re

from typing import TYPE_CHECKING

import httpretty
import pytest
import requests

from requests import codes

from poetry.inspection.lazy_wheel import HTTPRangeRequestUnsupported
from poetry.inspection.lazy_wheel import InvalidWheel
from poetry.inspection.lazy_wheel import memory_wheel_from_url
from tests.inspection.conftest import NEGATIVE_OFFSET_AS_POSITIVE


if TYPE_CHECKING:
    from tests.inspection.conftest import RequestCallbackFactory


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
def test_memory_wheel_from_url(
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

    wheel = memory_wheel_from_url("poetry-core", url, requests.Session())

    assert wheel.name == "poetry-core"
    assert wheel.version == "1.5.0"
    assert wheel.author == "Sébastien Eustace"
    assert wheel.requires_dist == [
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
    memory_wheel_from_url("poetry-core", url, requests.Session())
    expected_requests = min(expected_requests, 4)
    latest_requests = httpretty.latest_requests()
    assert len(latest_requests) == expected_requests


@pytest.mark.parametrize("negative_offset_as_positive", [False, True])
def test_memory_wheel_from_url_smaller_than_initial_chunk_size(
    http: type[httpretty.httpretty],
    handle_request_factory: RequestCallbackFactory,
    negative_offset_as_positive: bool,
) -> None:
    domain = f"tiny-wheel-{str(negative_offset_as_positive).lower()}.com"
    uri_regex = re.compile(f"^https://{domain}/.*$")
    request_callback = handle_request_factory(
        negative_offset_error=(
            (NEGATIVE_OFFSET_AS_POSITIVE, b"") if negative_offset_as_positive else None
        )
    )
    http.register_uri(http.GET, uri_regex, body=request_callback)
    http.register_uri(http.HEAD, uri_regex, body=request_callback)

    url = f"https://{domain}/zipp-3.5.0-py3-none-any.whl"

    wheel = memory_wheel_from_url("zipp", url, requests.Session())

    assert wheel.name == "zipp"
    assert wheel.version == "3.5.0"
    assert wheel.author == "Jason R. Coombs"
    assert len(wheel.requires_dist) == 12

    # only one request because server gives a normal response with the entire wheel
    # except for when server interprets negative offset as positive
    latest_requests = http.latest_requests()
    assert len(latest_requests) == 1


@pytest.mark.parametrize("accept_ranges", [None, "none"])
def test_memory_wheel_from_url_range_requests_not_supported_one_request(
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
        memory_wheel_from_url("poetry-core", url, requests.Session())

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
def test_memory_wheel_from_url_range_requests_not_supported_two_requests(
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
        memory_wheel_from_url("poetry-core", url, requests.Session())

    latest_requests = http.latest_requests()
    assert len(latest_requests) == 2
    assert latest_requests[0].method == "GET"
    assert latest_requests[1].method == "HEAD"


def test_memory_wheel_from_url_invalid_wheel(
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
        memory_wheel_from_url("demo-missing-dist-info", url, requests.Session())

    latest_requests = http.latest_requests()
    assert len(latest_requests) == 1
    assert latest_requests[0].method == "GET"
