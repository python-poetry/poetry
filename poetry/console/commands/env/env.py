from ..command import Command
from .info import EnvInfoCommand
from .list import EnvListCommand
from .remove import EnvRemoveCommand
from .use import EnvUseCommand


class EnvCommand(Command):

    name = "env"
    description = "Interact with Poetry's project environments."

    commands = [EnvInfoCommand(), EnvListCommand(), EnvRemoveCommand(), EnvUseCommand()]

    def handle(self):  # type: () -> int
        return self.call("help", self._config.name)
