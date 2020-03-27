from ..command import Command
from .clear import CacheClearCommand


class CacheCommand(Command):

    name = "cache"
    description = "Interact with Poetry's cache"

    commands = [CacheClearCommand()]

    def handle(self):
        return self.call("help", self._config.name)
