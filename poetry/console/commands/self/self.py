from ..command import Command

from .update import SelfUpdateCommand


class SelfCommand(Command):
    """
    Interact with Poetry directly.
    """

    name = "self"

    commands = [SelfUpdateCommand()]

    def handle(self):
        return self.call("help", self._config.name)
