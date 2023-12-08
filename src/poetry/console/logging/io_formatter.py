from __future__ import annotations

import logging
import os
import sys
import textwrap

from typing import TYPE_CHECKING

from poetry.console.logging.filters import POETRY_FILTER
from poetry.console.logging.formatters import FORMATTERS


if TYPE_CHECKING:
    from logging import LogRecord


class IOFormatter(logging.Formatter):
    _colors = {
        "error": "fg=red",
        "warning": "fg=yellow",
        "debug": "debug",
        "info": "fg=blue",
    }

    def format(self, record: LogRecord) -> str:
        if not record.exc_info:
            level = record.levelname.lower()
            msg = record.msg

            if record.name in FORMATTERS:
                msg = FORMATTERS[record.name].format(msg)
            elif level in self._colors:
                msg = f"<{self._colors[level]}>{msg}</>"

            record.msg = msg

        formatted = super().format(record)

        if not POETRY_FILTER.filter(record):
            # prefix all lines from third-party packages for easier debugging
            formatted = textwrap.indent(
                formatted, f"[{_log_prefix(record)}] ", lambda line: True
            )

        return formatted


def _log_prefix(record: LogRecord) -> str:
    prefix = _path_to_package(record.pathname) or record.module
    if record.name != "root":
        prefix = ":".join([prefix, record.name])
    return prefix


def _path_to_package(pathname: str) -> str | None:
    """Return main package name from the LogRecord.pathname."""
    # strip any file extension
    module = os.path.splitext(pathname)[0]
    # strip first matching python path from the pathname
    for syspath in sys.path:
        if pathname.startswith(syspath):
            module = module[len(syspath) :].lstrip(os.sep)
            break
    else:
        # this is unexpected, but let's play it safe
        return None
    module = module.partition(os.sep)[0]  # main package name
    return module
