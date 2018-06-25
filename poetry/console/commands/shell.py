from os import environ
from distutils.util import strtobool

from .venv_command import VenvCommand


class ShellCommand(VenvCommand):
    """
    Spawns a shell within the virtual environment.

    shell [options]
    """

    help = """The <info>shell</> command spawns a shell, according to the
<comment>$SHELL</> environment variable, within the virtual environment.
If one doesn't exist yet, it will be created.
"""

    def handle(self):
        from poetry.utils.shell import Shell

        # Check if it's already activated or doesn't exist and won't be created
        if strtobool(environ.get("POETRY_ACTIVE", "0")) or not self.venv.is_venv():
            current_venv = environ.get("VIRTUAL_ENV")

            if current_venv:
                self.line(
                    "Virtual environment already activated: "
                    "<info>{}</>".format(current_venv)
                )

            else:
                self.error("Virtual environment wasn't found")

            return

        self.line("Spawning shell within <info>{}</>".format(self.venv.venv))

        # Setting this to avoid spawning unnecessary nested shells
        environ["POETRY_ACTIVE"] = "1"
        shell = Shell.get()
        self.venv.execute(shell.path)
        environ.pop("POETRY_ACTIVE")
