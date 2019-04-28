from poetry.utils.alias import AliasManager

from ..command import Command


class AliasPruneCommand(Command):
    """
    Remove all alias definitions that no longer point to a project directory.

    prune
    """

    def handle(self):  # type: () -> None
        manager = AliasManager()
        removed_aliases = manager.prune()

        if not removed_aliases:
            self.line("No dangling aliases found.")
            return 0

        self.line("<b>Removed Aliases</b>")
        for name in sorted(removed_aliases):
            self.line("<info>{}</info>: {}".format(name, removed_aliases[name]))
