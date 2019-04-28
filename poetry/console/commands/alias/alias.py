from ..command import Command

from .go import AliasGoCommand
from .list import AliasListCommand
from .prune import AliasPruneCommand
from .rm import AliasRmCommand
from .set import AliasSetCommand
from .show import AliasShowCommand


class AliasCommand(Command):
    """
    Work with Poetry's project aliases.

    alias
    """

    commands = [
        AliasGoCommand(),
        AliasListCommand(),
        AliasPruneCommand(),
        AliasRmCommand(),
        AliasSetCommand(),
        AliasShowCommand(),
    ]

    def handle(self):  # type: () -> int
        return self.call("help", self._config.name)
