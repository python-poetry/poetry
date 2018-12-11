from ..command import Command

from .info import EnvInfoCommand
from .list import EnvListCommand
from .use import EnvUseCommand


class EnvCommand(Command):
    """
    Interact with Poetry's project environments.

    env
    """

    commands = [EnvInfoCommand(), EnvListCommand(), EnvUseCommand()]

    def handle(self):  # type: () -> int
        return self.call("help", self._config.name)
