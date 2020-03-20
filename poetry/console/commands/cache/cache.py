from poetry.console.commands.cache.list import CacheListCommand

from ..command import Command
from .clear import CacheClearCommand


class CacheCommand(Command):

    name = "cache"
    description = "Interact with Poetry's cache"

    commands = [CacheClearCommand(), CacheListCommand()]

    def handle(self):
        return self.call("help", self._config.name)
