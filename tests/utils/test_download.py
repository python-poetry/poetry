from __future__ import annotations

import base64
import re

from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar
from typing import Literal

import pytest
import responses

from requests.exceptions import ChunkedEncodingError

from poetry.utils.download import Downloader
from poetry.utils.download import HTTPRangeRequestSupportedError
from poetry.utils.download import download_file
from poetry.utils.helpers import get_file_hash


if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from requests import PreparedRequest

    from poetry.config.config import Config
    from tests.types import FixtureDirGetter
    from tests.types import HttpResponse


def test_download_file(
    http: responses.RequestsMock, fixture_dir: FixtureDirGetter, tmp_path: Path
) -> None:
    file_path = fixture_dir("distributions") / "demo-0.1.0.tar.gz"
    url = "https://foo.com/demo-0.1.0.tar.gz"
    http.get(url, body=file_path.read_bytes())
    dest = tmp_path / "demo-0.1.0.tar.gz"

    download_file(url, dest)

    expect_sha_256 = "9fa123ad707a5c6c944743bf3e11a0e80d86cb518d3cf25320866ca3ef43e2ad"
    assert get_file_hash(dest) == expect_sha_256
    assert http.calls[-1].request.headers["Accept-Encoding"] == "Identity"


def test_downloader_with_invalid_content_length(
    http: responses.RequestsMock, tmp_path: Path
) -> None:
    url = "https://foo.com/demo.txt"
    http.get(url, body=b"demo", headers={"Content-Length": "invalid"})
    dest = tmp_path / "demo.txt"

    downloader = Downloader(url, dest)

    assert downloader.total_size == 0
    assert list(downloader.download_with_progress(chunk_size=2)) == [2, 4]
    assert dest.read_bytes() == b"demo"


def test_download_file_recover_from_error(
    http: responses.RequestsMock, fixture_dir: FixtureDirGetter, tmp_path: Path
) -> None:
    file_path = fixture_dir("distributions") / "demo-0.1.0.tar.gz"
    file_body = file_path.read_bytes()
    file_length = len(file_body)
    url = "https://foo.com/demo-0.1.0.tar.gz"

    def handle_request(request: PreparedRequest) -> HttpResponse:
        if request.headers.get("Range") is None:
            response_headers = {
                "Content-Length": str(file_length),
                "Accept-Ranges": "bytes",
            }
            return 200, response_headers, file_body[: file_length // 2]
        else:
            start = int(
                request.headers.get("Range", "bytes=0-").split("=")[1].split("-")[0]
            )
            response_headers = {"Content-Length": str(len(file_body[start:]))}
            return 206, response_headers, file_body[start:]

    http.add_callback(responses.GET, url, callback=handle_request)
    dest = tmp_path / "demo-0.1.0.tar.gz"

    download_file(url, dest, chunk_size=file_length // 2, max_retries=1)

    expect_sha_256 = "9fa123ad707a5c6c944743bf3e11a0e80d86cb518d3cf25320866ca3ef43e2ad"
    assert get_file_hash(dest) == expect_sha_256
    assert http.calls[-1].request.headers["Accept-Encoding"] == "Identity"
    assert http.calls[-1].request.headers["Range"] == f"bytes={file_length // 2}-"


def test_download_file_fail_when_no_range(
    http: responses.RequestsMock, fixture_dir: FixtureDirGetter, tmp_path: Path
) -> None:
    file_path = fixture_dir("distributions") / "demo-0.1.0.tar.gz"
    file_body = file_path.read_bytes()
    file_length = len(file_body)
    url = "https://foo.com/demo-0.1.0.tar.gz"

    def handle_request(request: PreparedRequest) -> HttpResponse:
        response_headers = {"Content-Length": str(file_length)}
        return 200, response_headers, file_body[: file_length // 2]

    http.add_callback(responses.GET, url, callback=handle_request)
    dest = tmp_path / "demo-0.1.0.tar.gz"
    with pytest.raises(ChunkedEncodingError):
        download_file(url, dest, chunk_size=file_length // 2, max_retries=1)


def test_download_file_fail_when_first_chunk_failed(
    http: responses.RequestsMock, fixture_dir: FixtureDirGetter, tmp_path: Path
) -> None:
    file_path = fixture_dir("distributions") / "demo-0.1.0.tar.gz"
    file_body = file_path.read_bytes()
    file_length = len(file_body)
    url = "https://foo.com/demo-0.1.0.tar.gz"

    def handle_request(request: PreparedRequest) -> tuple[int, dict[str, Any], bytes]:
        response_headers = {
            "Content-Length": str(file_length),
            "Accept-Ranges": "bytes",
        }
        return 200, response_headers, file_body[: file_length // 2]

    http.add_callback(responses.GET, url, callback=handle_request)
    dest = tmp_path / "demo-0.1.0.tar.gz"
    with pytest.raises(ChunkedEncodingError):
        download_file(url, dest, chunk_size=file_length, max_retries=1)


@pytest.mark.parametrize("accepts_ranges", [False, True])
@pytest.mark.parametrize("raise_accepts_ranges", [False, True])
def test_download_file_raise_accepts_ranges(
    http: responses.RequestsMock,
    fixture_dir: FixtureDirGetter,
    tmp_path: Path,
    accepts_ranges: bool,
    raise_accepts_ranges: bool,
) -> None:
    filename = "demo-0.1.0-py2.py3-none-any.whl"

    def handle_request(request: PreparedRequest) -> tuple[int, dict[str, Any], bytes]:
        file_path = fixture_dir("distributions") / filename
        response_headers = {}
        if accepts_ranges:
            response_headers["Accept-Ranges"] = "bytes"
        return 200, response_headers, file_path.read_bytes()

    url = f"https://foo.com/{filename}"
    http.add_callback(responses.GET, url, callback=handle_request)
    dest = tmp_path / filename

    if accepts_ranges and raise_accepts_ranges:
        with pytest.raises(HTTPRangeRequestSupportedError):
            download_file(url, dest, raise_accepts_ranges=raise_accepts_ranges)
        assert not dest.exists()
    else:
        download_file(url, dest, raise_accepts_ranges=raise_accepts_ranges)
        assert dest.is_file()


def test_downloader_uses_authenticator_by_default(
    config: Config,
    http: responses.RequestsMock,
    tmp_working_directory: Path,
) -> None:
    import poetry.utils.authenticator

    # force set default authenticator to None so that it is recreated using patched config
    poetry.utils.authenticator._authenticator = None

    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/files/"}},
            "http-basic": {"foo": {"username": "bar", "password": "baz"}},
        }
    )

    http.get(
        re.compile("^https?://foo.bar/(.+?)$"),
    )

    Downloader(
        "https://foo.bar/files/foo-0.1.0.tar.gz",
        tmp_working_directory / "foo-0.1.0.tar.gz",
    )

    request = http.calls[-1].request
    basic_auth = base64.b64encode(b"bar:baz").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_downloader_retries_only_the_resumable_requests_errors(tmp_path: Path) -> None:
    import requests.exceptions

    def run_with(exc: type[BaseException]) -> int:
        state = {"n": 0}

        class _Resp:
            headers: ClassVar[dict[str, str]] = {
                "Accept-Ranges": "bytes",
                "Content-Length": "8",
            }

            def raise_for_status(self) -> None: ...
            def close(self) -> None: ...
            def __enter__(self) -> _Resp:
                return self

            def __exit__(self, *_: object) -> Literal[False]:
                return False

            def iter_content(self, chunk_size: int = 1) -> Iterator[bytes]:
                state["n"] += 1
                yield b"ab"
                if state["n"] == 1:
                    raise exc("stub failure")

        class _Session:
            def get(self, *_: object, **__: object) -> _Resp:
                return _Resp()

        downloader = Downloader(
            "https://example.invalid/x",
            tmp_path / "out.bin",
            session=_Session(),  # type: ignore[arg-type]
            max_retries=2,
        )
        list(downloader.download_with_progress(chunk_size=2))
        return state["n"]

    assert run_with(requests.exceptions.ConnectionError) == 2
    assert run_with(requests.exceptions.ChunkedEncodingError) == 2
    assert run_with(requests.exceptions.SSLError) == 2

    for exc in (ValueError, AttributeError):
        with pytest.raises(exc):
            run_with(exc)


def test_downloader_stops_after_max_retries(tmp_path: Path) -> None:
    import requests.exceptions

    state = {"n": 0}

    class _Resp:
        headers: ClassVar[dict[str, str]] = {
            "Accept-Ranges": "bytes",
            "Content-Length": "8",
        }

        def raise_for_status(self) -> None: ...
        def close(self) -> None: ...
        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *_: object) -> Literal[False]:
            return False

        def iter_content(self, chunk_size: int = 1) -> Iterator[bytes]:
            state["n"] += 1
            yield b"ab"
            raise requests.exceptions.ConnectionError("stub failure")

    class _Session:
        def get(self, *_: object, **__: object) -> _Resp:
            return _Resp()

    downloader = Downloader(
        "https://example.invalid/x",
        tmp_path / "out.bin",
        session=_Session(),  # type: ignore[arg-type]
        max_retries=2,
    )
    with pytest.raises(requests.exceptions.ConnectionError):
        list(downloader.download_with_progress(chunk_size=2))

    assert state["n"] == 3
