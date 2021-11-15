import logging


class Formatter:
    def format(self, record: logging.LogRecord) -> str:
        raise NotImplementedError()
