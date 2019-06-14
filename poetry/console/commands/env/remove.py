from cleo import argument

from ..command import Command


class EnvRemoveCommand(Command):

    name = "remove"
    description = "Remove a specific virtualenv associated with the project."

    arguments = [
        argument("python", "The python executable to remove the virtualenv for.")
    ]

    def handle(self):
        from poetry.utils.env import EnvManager

        poetry = self.poetry
        manager = EnvManager(poetry.config)
        venv = manager.remove(self.argument("python"), poetry.file.parent)

        self.line("Deleted virtualenv: <comment>{}</comment>".format(venv.path))
