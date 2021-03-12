import logging


class Formatter(object):
    def format(self, record: logging.LogRecord) -> str:
        raise NotImplementedError()
