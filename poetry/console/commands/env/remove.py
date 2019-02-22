from ..command import Command


class EnvRemoveCommand(Command):
    """
    Remove a specific virtualenv associated with the project.

    remove
        {python : The python executable to remove the virtualenv for.}
    """

    def handle(self):
        from poetry.utils.env import EnvManager

        poetry = self.poetry
        manager = EnvManager(poetry.config)
        venv = manager.remove(self.argument("python"), poetry.file.parent)

        self.line("Deleted virtualenv: <comment>{}</comment>".format(venv.path))
