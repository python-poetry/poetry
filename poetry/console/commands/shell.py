from .venv_command import VenvCommand


class ShellCommand(VenvCommand):
    """
    Spawns a shell within the virtual environment.

    shell [options]
    """

    help = """The <info>shell</info> command spawns a shell, according to the
<comment>$SHELL</> environment variable, within the virtual environment.
If one doesn't exist yet, it will be created.
"""

    def handle(self):
        if self.venv.is_venv():
            self.line(f"Spawning shell within <info>{self.venv.venv}</info>")

            shell = self.venv.get_shell()
            self.venv.execute(shell)

        else:
            self.line("Virtual environment already activated.")
