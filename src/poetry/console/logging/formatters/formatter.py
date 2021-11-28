from typing import TYPE_CHECKING


if TYPE_CHECKING:
    import logging


class Formatter:
    def format(self, record: "logging.LogRecord") -> str:
        raise NotImplementedError()
