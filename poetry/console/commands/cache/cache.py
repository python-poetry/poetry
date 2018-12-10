from ..command import Command

from .clear import CacheClearCommand


class CacheCommand(Command):
    """
    Interact with Poetry's cache.

    cache
    """

    commands = [CacheClearCommand()]

    def handle(self):
        return self.call("help", self._config.name)
