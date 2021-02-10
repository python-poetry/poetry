import logging

from typing import TYPE_CHECKING

from .formatters import FORMATTERS


if TYPE_CHECKING:
    from logging import LogRecord


class IOFormatter(logging.Formatter):

    _colors = {
        "error": "fg=red",
        "warning": "fg=yellow",
        "debug": "debug",
        "info": "fg=blue",
    }

    def format(self, record: "LogRecord") -> str:
        if not record.exc_info:
            level = record.levelname.lower()
            msg = record.msg

            if record.name in FORMATTERS:
                msg = FORMATTERS[record.name].format(msg)
            elif level in self._colors:
                msg = "<{}>{}</>".format(self._colors[level], msg)

            return msg

        return super(IOFormatter, self).format(record)
