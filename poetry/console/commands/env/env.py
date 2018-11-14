from ..command import Command

from .info import EnvInfoCommand


class EnvCommand(Command):
    """
    Interact with Poetry's project environments.

    env
    """

    commands = [EnvInfoCommand()]

    def handle(self):  # type: () -> int
        return self.call("help", self._config.name)
