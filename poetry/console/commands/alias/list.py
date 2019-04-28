from poetry.utils.alias import AliasManager

from ..command import Command


class AliasListCommand(Command):
    """
    List all defined project aliases.

    list
    """

    def handle(self):  # type: () -> None
        manager = AliasManager()
        aliases = manager.list()

        for name in sorted(aliases):
            self.line("<info>{}</info>: {}".format(name, aliases[name]))
