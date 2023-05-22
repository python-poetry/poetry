from __future__ import annotations

from cleo.helpers import argument
from cleo.helpers import option

from poetry.console.commands.command import Command


class EnvRemoveCommand(Command):
    name = "env remove"
    description = "Remove virtual environments associated with the project."

    arguments = [
        argument(
            "python",
            (
                "The python executables associated with, or names of the virtual"
                " environments which are to be removed."
            ),
            optional=True,
            multiple=True,
        )
    ]
    options = [
        option(
            "all",
            description=(
                "Remove all managed virtual environments associated with the project."
            ),
        ),
    ]

    def handle(self) -> int:
        from poetry.utils.env import EnvManager

        pythons = self.argument("python")
        all = self.option("all")
        if not (pythons or all):
            self.line("No virtualenv provided.")

        manager = EnvManager(self.poetry)
        # TODO: refactor env.py to allow removal with one loop
        for python in pythons:
            venv = manager.remove(python)
            self.line(f"Deleted virtualenv: <comment>{venv.path}</comment>")
        if all:
            for venv in manager.list():
                manager.remove_venv(venv.path)
                self.line(f"Deleted virtualenv: <comment>{venv.path}</comment>")

        return 0
