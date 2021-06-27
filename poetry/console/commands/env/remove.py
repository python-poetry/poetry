from cleo.helpers import argument

from ..command import Command


class EnvRemoveCommand(Command):

    name = "env remove"
    description = "Removes a specific virtualenv associated with the project."

    arguments = [
        argument("python", "The python executable to remove the virtualenv for.")
    ]

    def handle(self) -> None:
        from poetry.utils.env import EnvManager

        manager = EnvManager(self.poetry)
        venv = manager.remove(self.argument("python"))

        self.line("Deleted virtualenv: <comment>{}</comment>".format(venv.path))
