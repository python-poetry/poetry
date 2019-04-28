from poetry.utils.alias import AliasManager

from ..command import Command


class AliasShowCommand(Command):
    """
    Show the alias for the current project.

    show
    """

    def handle(self):  # type: () -> None
        manager = AliasManager(self.poetry.config)
        project_path = self.poetry.file.parent
        name = manager.get_alias(project_path)
        self.line(name)
