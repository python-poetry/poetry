import logging


class IOHandler(logging.Handler):
    def __init__(self, io):
        self._io = io

        level = logging.WARNING
        if io.is_debug():
            level = logging.DEBUG
        elif io.is_very_verbose() or io.is_verbose():
            level = logging.INFO

        super(IOHandler, self).__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            level = record.levelname.lower()
            err = level in ("warning", "error", "exception", "critical")
            if err:
                self._io.error_line(msg)
            else:
                self._io.write_line(msg)
        except Exception:
            self.handleError(record)
