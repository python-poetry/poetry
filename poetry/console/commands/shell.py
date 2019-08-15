import sys

from os import environ
from distutils.util import strtobool

from .env_command import EnvCommand


class ShellCommand(EnvCommand):
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
        venv_activated = strtobool(environ.get("POETRY_ACTIVE", "0")) or getattr(
            sys, "real_prefix", sys.prefix
        ) == str(self.env.path)
        if venv_activated:
            self.line(
                "Virtual environment already activated: "
                "<info>{}</>".format(self.env.path)
            )

            return

        self.line("Spawning shell within <info>{}</>".format(self.env.path))

        # Setting this to avoid spawning unnecessary nested shells
        environ["POETRY_ACTIVE"] = "1"
        shell = Shell.get()
        self.env.execute(shell.path)
        environ.pop("POETRY_ACTIVE")
