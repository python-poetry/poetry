from cleo import argument
from cleo import option

from ..command import Command


class EnvRemoveCommand(Command):

    name = "remove"
    description = "Removes specific virtual environments associated with the project."

    arguments = [
        argument(
            "python",
            "The python executables to remove the virtualenv for.",
            optional=True,
            multiple=True,
        )
    ]
    options = [
        option("all", description="Remove all virtualenv associated with the project."),
    ]

    def handle(self):
        from poetry.utils.env import EnvManager

        manager = EnvManager(self.poetry)
        pythons = self.argument("python")
        all = self.option("all")
        if all:
            pythons = [x.path.name for x in manager.list()]
        if not pythons:
            self.line("No virtualenv provided.")
        for python in pythons:
            venv = manager.remove(python)
            self.line("Deleted virtualenv: <comment>{}</comment>".format(venv.path))
