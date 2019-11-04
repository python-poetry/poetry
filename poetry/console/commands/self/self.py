from ..command import Command
from .update import SelfUpdateCommand


class SelfCommand(Command):

    name = "self"
    description = "Interact with Poetry directly."

    commands = [SelfUpdateCommand()]

    def handle(self):
        return self.call("help", self._config.name)
