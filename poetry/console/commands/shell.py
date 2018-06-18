from os import environ

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
        current_venv = environ.get("POETRY_ACTIVE")

        if not current_venv and not self.venv.is_venv():
            current_venv = environ.get("VIRTUAL_ENV")

        if current_venv:
            self.line(
                "Virtual environment already activated: "
                "<info>{}</>".format(current_venv)
            )
            return

        if self.venv._windows:
            shell, *args = ("cmd", "/k")
        else:
            shell, *args = (environ.get("SHELL"),)
            if shell is None:
                self.error("The SHELL environment variable must be set.")
                return

        self.line("Spawning shell within <info>{}</>".format(self.venv.venv))

        environ["POETRY_ACTIVE"] = str(self.venv.venv)
        self.venv.execute(shell, *args)
        environ.pop("POETRY_ACTIVE")
