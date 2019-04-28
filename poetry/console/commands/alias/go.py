import sys

from os import chdir, environ
from distutils.util import strtobool

from poetry.utils._compat import Path
from poetry.utils.alias import AliasManager

from ..command import Command


class AliasGoCommand(Command):
    """
    Activate a project's virtualenv and change to its source directory.

    go
        {name : The alias of the project to activate.}
    """

    def handle(self):  # type: () -> None
        # Don't do anything if we are already inside a virtualenv
        active_venv = environ.get("VIRTUAL_ENV", None)

        if active_venv is not None:
            self.line(
                "Virtual environment already activated: "
                "<info>{}</>".format(active_venv)
            )
            return

        # Determine the project path for the given alias
        manager = AliasManager()
        name = self.argument("name")
        project_path = manager.get_project(name)
        project_dirname = str(project_path)

        # Change directory and activate the virtualenv
        chdir(project_dirname)
        environ["PWD"] = project_dirname
        self.call("shell")
