from poetry.utils.alias import AliasManager

from ..command import Command


class AliasSetCommand(Command):
    """
    Set an alias for the current project.

    set
        {name : The alias to set for the current project.}
    """

    def handle(self):  # type: () -> None
        manager = AliasManager(self.poetry.config)
        project_path = self.poetry.file.parent
        name = self.argument("name")
        manager.set(project_path, name)
