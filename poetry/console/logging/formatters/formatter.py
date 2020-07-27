import logging


class Formatter(object):
    def format(self, record):  # type: (logging.LogRecord) -> str
        raise NotImplementedError()
