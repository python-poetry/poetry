from __future__ import annotations

import subprocess
import sys
import tempfile

from pathlib import Path
from typing import TYPE_CHECKING
from typing import ClassVar
from typing import Literal

import pytest

from poetry.utils import helpers
from poetry.utils.download import Downloader
from poetry.utils.download import download_file


if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.mark.parametrize(
    ("name", "expected"),
    [("Downloader", Downloader), ("download_file", download_file)],
)
def test_deprecated_helpers_download_reexports(name: str, expected: object) -> None:
    with pytest.warns(DeprecationWarning, match="poetry.utils.download"):
        assert getattr(helpers, name) is expected
    assert name in dir(helpers)


def test_unknown_helpers_attribute_still_raises_attribute_error() -> None:
    with pytest.raises(AttributeError):
        helpers.definitely_not_a_real_attribute  # noqa: B018


def test_importing_the_cli_entrypoint_does_not_import_requests() -> None:
    code = (
        "import sys;"
        "import poetry.console.application;"
        "print('requests' in sys.modules, 'urllib3' in sys.modules)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out == "False False", f"expected neither to be imported, got {out}"


def test_downloader_retries_only_the_resumable_requests_errors() -> None:
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

        with tempfile.TemporaryDirectory() as td:
            downloader = Downloader(
                "https://example.invalid/x",
                Path(td) / "out.bin",
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


def test_downloader_stops_after_max_retries() -> None:
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

    with tempfile.TemporaryDirectory() as td:
        downloader = Downloader(
            "https://example.invalid/x",
            Path(td) / "out.bin",
            session=_Session(),  # type: ignore[arg-type]
            max_retries=2,
        )
        with pytest.raises(requests.exceptions.ConnectionError):
            list(downloader.download_with_progress(chunk_size=2))

    assert state["n"] == 3
