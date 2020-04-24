from cleo import argument
from cleo import option
from clikit.api.args.exceptions import CannotParseArgsException

from ..command import Command


class EnvRemoveCommand(Command):

    name = "remove"
    description = "Removes a specific virtualenv associated with the project."

    arguments = [
        argument(
            "python",
            "The python executable to remove the virtualenv for.",
            optional=True,
        )
    ]

    options = [option("all", None, "Remove of virtualenvs of this project.")]

    def handle(self):
        from poetry.utils.env import EnvManager

        manager = EnvManager(self.poetry)
        if self.option("all"):
            for venv in manager.list():
                manager.remove(venv.path.name)
                self.line("Deleted virtualenv: <comment>{}</comment>".format(venv.path))
        else:
            # simulate a non-optional argument - it needs to be optional for --all to work
            # but required for deleting individual environments
            if self.argument("python") is None:
                raise CannotParseArgsException(
                    'Not enough arguments (missing: "python").'
                )

            venv = manager.remove(self.argument("python"))

            self.line("Deleted virtualenv: <comment>{}</comment>".format(venv.path))
