from poetry.utils.alias import AliasManager

from ..command import Command


class AliasCleanCommand(Command):
    """
    Remove all alias definitions that no longer point to a project directory.

    clean
    """

    def handle(self):  # type: () -> None
        manager = AliasManager()
        removed_aliases = manager.clean()

        if not removed_aliases:
            self.line("No aliases defined.")
            return 0

        self.line("<b>Removed Aliases</b>")
        for name in sorted(removed_aliases):
            self.line("<info>{}</info>: {}".format(name, removed_aliases[name]))
