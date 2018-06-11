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
        if self.venv.is_venv():
            if self.venv._windows:
                self.venv.execute("cmd", "/k")

            else:
                shell = self.venv.get_shell()
                if shell is None:
                    self.error("SHELL environment variable must be set.")
                    return
                self.venv.execute(shell)

            self.line("Spawning shell within <info>{}</>".format(self.venv.venv))

        else:
            self.line("Virtual environment already activated.")
