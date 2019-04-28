from poetry.utils.alias import AliasManager

from ..command import Command


class AliasRmCommand(Command):
    """
    Remove the alias for the current project.

    rm
        {alias? : The alias to remove.  If omitted, remove the current project's alias.}
    """

    def handle(self):  # type: () -> None
        manager = AliasManager()
        alias = self.argument("alias")

        if alias:
            project_path = manager.get_project(alias)
        else:
            project_path = self.poetry.file.parent

        manager.remove(project_path)
