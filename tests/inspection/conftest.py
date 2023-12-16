from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import Protocol
from typing import Tuple
from urllib.parse import urlparse

import pytest

from requests import codes


if TYPE_CHECKING:
    from collections.abc import Callable

    from httpretty.core import HTTPrettyRequest

    from tests.types import FixtureDirGetter

    HttPrettyResponse = Tuple[int, Dict[str, Any], bytes]  # status code, headers, body
    HttPrettyRequestCallback = Callable[
        [HTTPrettyRequest, str, Dict[str, Any]], HttPrettyResponse
    ]

    class RequestCallbackFactory(Protocol):
        def __call__(
            self,
            *,
            accept_ranges: str | None = "bytes",
            negative_offset_error: tuple[int, bytes] | None = None,
        ) -> HttPrettyRequestCallback: ...


NEGATIVE_OFFSET_AS_POSITIVE = -1


def build_head_response(
    accept_ranges: str | None, content_length: int, response_headers: dict[str, Any]
) -> HttPrettyResponse:
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
) -> HttPrettyResponse:
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
        rng_parts = rng.split("-")
        start = int(rng_parts[0])
        end = int(rng_parts[1])
        body = wheel_bytes[start : end + 1]
    response_headers["Content-Range"] = f"bytes {start}-{end}/{total_length}"
    return status_code, response_headers, body


@pytest.fixture
def handle_request_factory(fixture_dir: FixtureDirGetter) -> RequestCallbackFactory:
    def _factory(
        *,
        accept_ranges: str | None = "bytes",
        negative_offset_error: tuple[int, bytes] | None = None,
    ) -> HttPrettyRequestCallback:
        def handle_request(
            request: HTTPrettyRequest, uri: str, response_headers: dict[str, Any]
        ) -> HttPrettyResponse:
            name = Path(urlparse(uri).path).name

            wheel = Path(__file__).parent.parent.joinpath(
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

            rng = request.headers.get("Range", "")
            if rng:
                rng = rng.split("=")[1]

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
