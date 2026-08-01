from __future__ import annotations

import subprocess
import sys

from typing import ClassVar

import pytest

from typing_extensions import Self

from poetry.utils import helpers


LAZY_NAMES = [
    "ChunkedEncodingError",
    "ConnectionError",
    "atomic_open",
    "get_default_authenticator",
]


@pytest.mark.parametrize("name", LAZY_NAMES)
def test_lazily_reexported_names_are_still_importable(name: str) -> None:
    """These were module-level imports and stay part of the module's public surface."""
    assert hasattr(helpers, name)
    assert name in dir(helpers)


@pytest.mark.parametrize("name", LAZY_NAMES)
def test_lazily_reexported_names_resolve_to_the_real_objects(name: str) -> None:
    import requests.exceptions
    import requests.utils

    from poetry.utils import authenticator

    expected = {
        "ChunkedEncodingError": requests.exceptions.ChunkedEncodingError,
        "ConnectionError": requests.exceptions.ConnectionError,
        "atomic_open": requests.utils.atomic_open,
        "get_default_authenticator": authenticator.get_default_authenticator,
    }[name]
    assert getattr(helpers, name) is expected


def test_unknown_attribute_still_raises_attribute_error() -> None:
    with pytest.raises(AttributeError):
        helpers.definitely_not_a_real_attribute  # noqa: B018


def test_importing_the_cli_entrypoint_does_not_import_requests() -> None:
    """The CLI imports this module for two filesystem helpers, so it must not drag the
    HTTP stack in. This is the regression the lazy imports exist to prevent."""
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
    """`except ConnectionError` inside this module must be the requests class, not the
    builtin. A module-level ``__getattr__`` serves attribute access on the module object
    but never bare global lookup inside the module's own functions, so a lazy rewrite can
    silently bind the builtin -- which requests' ConnectionError is not a subclass of --
    and stop retrying resumable downloads."""
    import requests.exceptions

    def run_with(exc: type[BaseException], tmp_path_factory: object = None) -> int:
        import tempfile

        from pathlib import Path

        state = {"n": 0}

        class _Resp:
            headers: ClassVar[dict[str, str]] = {
                "Accept-Ranges": "bytes",
                "Content-Length": "8",
            }

            def raise_for_status(self) -> None: ...
            def close(self) -> None: ...
            def __enter__(self) -> Self:
                return self

            def __exit__(self, *_: object) -> bool:
                return False

            def iter_content(self, chunk_size: int = 1):
                state["n"] += 1
                yield b"ab"
                if state["n"] == 1:
                    raise exc("stub failure")

        class _Session:
            def get(self, *_: object, **__: object) -> _Resp:
                return _Resp()

        with tempfile.TemporaryDirectory() as td:
            downloader = helpers.Downloader(
                "https://example.invalid/x",
                Path(td) / "out.bin",
                session=_Session(),  # type: ignore[arg-type]
                max_retries=2,
            )
            list(downloader.download_with_progress(chunk_size=2))
        return state["n"]

    # Retried on unmodified main, so the stub is asked for content twice. SSLError is
    # included deliberately: it subclasses requests' ConnectionError, so it is caught by
    # the same clause, and it is caught only if that name is the requests class rather
    # than the builtin.
    assert run_with(requests.exceptions.ConnectionError) == 2
    assert run_with(requests.exceptions.ChunkedEncodingError) == 2
    assert run_with(requests.exceptions.SSLError) == 2

    # Not resumable: must propagate rather than be swallowed by a broad except clause.
    for exc in (ValueError, AttributeError):
        with pytest.raises(exc):
            run_with(exc)
