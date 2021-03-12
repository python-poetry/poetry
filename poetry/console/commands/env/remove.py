from cleo.helpers import argument
from cleo.helpers import option

from ..command import Command


class EnvRemoveCommand(Command):

    name = "env remove"
    description = "Remove specific virtual environments associated with the project."

    arguments = [
        argument(
            "python",
            "The python executables of the virtual environments which are to be "
            "removed.",
            optional=True,
            multiple=True,
        )
    ]
    options = [
        option(
            "all",
            description="Remove all managed virtual environments associated with the "
            "project.",
        ),
    ]

    def handle(self) -> None:
        from poetry.utils.env import EnvManager

        pythons = self.argument("python")
        all = self.option("all")
        if not (pythons or all):
            self.line("No virtualenv provided.")

        manager = EnvManager(self.poetry)
        for python in pythons:
            venv = manager.remove(python)
            self.line("Deleted virtualenv: <comment>{}</comment>".format(venv.path))
        if all:
            for venv in manager.list():
                manager.remove_venv(venv.path)
                self.line("Deleted virtualenv: <comment>{}</comment>".format(venv.path))
