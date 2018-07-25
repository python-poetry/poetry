import logging

from cleo import Command as BaseCommand

from ..styles.poetry import PoetryStyle


class CommandFormatter(logging.Formatter):

    _colors = {
        "error": "fg=red",
        "warning": "fg=yellow",
        "debug": "debug",
        "info": "fg=blue",
    }

    def format(self, record):
        if not record.exc_info:
            level = record.levelname.lower()
            msg = record.msg

            if level in self._colors:
                msg = "<{}>{}</>".format(self._colors[level], msg)

            return msg

        return super(CommandFormatter, self).format(record)


class CommandHandler(logging.Handler):
    def __init__(self, command):
        self._command = command

        output = self._command.output
        level = logging.WARNING
        if output.is_debug():
            level = logging.DEBUG
        elif output.is_very_verbose() or output.is_verbose():
            level = logging.INFO

        super(CommandHandler, self).__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            level = record.levelname.lower()
            err = level in ("warning", "error", "exception", "critical")
            if err:
                self._command.output.write_error(msg, newline=True)
            else:
                self._command.line(msg)
        except Exception:
            self.handleError(record)


class Command(BaseCommand):

    _loggers = []

    @property
    def poetry(self):
        return self.get_application().poetry

    def reset_poetry(self):  # type: () -> None
        self.get_application().reset_poetry()

    def run(self, i, o):  # type: () -> int
        """
        Initialize command.
        """
        self.input = i
        self.output = PoetryStyle(i, o)

        for logger in self._loggers:
            self.register_logger(logging.getLogger(logger))

        return super(BaseCommand, self).run(i, o)

    def register_logger(self, logger):
        """
        Register a new logger.
        """
        handler = CommandHandler(self)
        handler.setFormatter(CommandFormatter())
        logger.handlers = [handler]
        logger.propagate = False

        output = self.output
        level = logging.WARNING
        if output.is_debug():
            level = logging.DEBUG
        elif output.is_very_verbose() or output.is_verbose():
            level = logging.INFO

        logger.setLevel(level)
