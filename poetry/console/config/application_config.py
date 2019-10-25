import logging

from cleo.config import ApplicationConfig as BaseApplicationConfig
from clikit.api.event import PRE_HANDLE
from clikit.api.event import PreHandleEvent
from clikit.api.formatter import Style

from poetry.console.commands.command import Command
from poetry.console.commands.env_command import EnvCommand
from poetry.console.logging import IOFormatter
from poetry.console.logging import IOHandler


class ApplicationConfig(BaseApplicationConfig):
    def configure(self):
        super(ApplicationConfig, self).configure()

        self.add_style(Style("c1").fg("cyan"))
        self.add_style(Style("info").fg("blue"))
        self.add_style(Style("comment").fg("green"))
        self.add_style(Style("error").fg("red").bold())
        self.add_style(Style("warning").fg("yellow"))
        self.add_style(Style("debug").fg("black").bold())

        self.add_event_listener(PRE_HANDLE, self.register_command_loggers)
        self.add_event_listener(PRE_HANDLE, self.set_env)

    def register_command_loggers(
        self, event, event_name, _  # type: PreHandleEvent  # type: str
    ):  # type: (...) -> None
        command = event.command.config.handler
        if not isinstance(command, Command):
            return

        io = event.io

        if not command.loggers:
            return

        handler = IOHandler(io)
        handler.setFormatter(IOFormatter())

        for logger in command.loggers:
            logger = logging.getLogger(logger)

            logger.handlers = [handler]
            logger.propagate = False

            level = logging.WARNING
            if io.is_debug():
                level = logging.DEBUG
            elif io.is_very_verbose() or io.is_verbose():
                level = logging.INFO

            logger.setLevel(level)

    def set_env(self, event, event_name, _):  # type: (PreHandleEvent, str, _) -> None
        from poetry.semver import parse_constraint
        from poetry.utils.env import EnvManager

        command = event.command.config.handler  # type: EnvCommand
        if not isinstance(command, EnvCommand):
            return

        io = event.io
        poetry = command.poetry

        env_manager = EnvManager(poetry)
        env = env_manager.create_venv(io)

        if env.is_venv() and io.is_verbose():
            io.write_line("Using virtualenv: <comment>{}</>".format(env.path))

        command.set_env(env)
