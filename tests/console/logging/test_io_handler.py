from __future__ import annotations

import logging

from logging import LogRecord
from typing import TYPE_CHECKING

import pytest

from cleo.io.buffered_io import BufferedIO

from poetry.console.logging.io_handler import IOHandler


if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def make_record(level: int, msg: str) -> LogRecord:
    return LogRecord("poetry", level, "syspath/foo.py", 0, msg, (), None)


def test_emit_writes_info_to_output() -> None:
    io = BufferedIO()
    handler = IOHandler(io)

    handler.emit(make_record(logging.INFO, "all good"))

    assert io.fetch_output() == "all good\n"
    assert io.fetch_error() == ""


@pytest.mark.parametrize("level", [logging.WARNING, logging.ERROR, logging.CRITICAL])
def test_emit_writes_severe_levels_to_error_output(level: int) -> None:
    io = BufferedIO()
    handler = IOHandler(io)

    handler.emit(make_record(level, "something broke"))

    assert io.fetch_output() == ""
    assert io.fetch_error() == "something broke\n"


def test_emit_uses_the_configured_formatter() -> None:
    io = BufferedIO()
    handler = IOHandler(io)
    handler.setFormatter(logging.Formatter("formatted: %(message)s"))

    handler.emit(make_record(logging.INFO, "raw"))

    assert io.fetch_output() == "formatted: raw\n"


def test_emit_passes_failures_to_handle_error(mocker: MockerFixture) -> None:
    io = BufferedIO()
    handler = IOHandler(io)
    mocker.patch.object(io, "write_line", side_effect=OSError("broken io"))
    handle_error = mocker.patch.object(handler, "handleError")
    record = make_record(logging.INFO, "never written")

    handler.emit(record)

    handle_error.assert_called_once_with(record)
