from poetry.installation import Installer

from .venv_command import VenvCommand


class LockCommand(VenvCommand):
    """
    Locks the project dependencies.

    lock
    """

    help = """The <info>lock</info> command reads the <comment>pyproject.toml</> file from
the current directory, processes it, and locks the depdencies in the <comment>pyproject.lock</> file.

<info>poetry lock</info>    
"""

    def handle(self):
        installer = Installer(
            self.output,
            self.venv,
            self.poetry.package,
            self.poetry.locker,
            self.poetry.pool
        )

        installer.update(True)
        installer.execute_operations(False)

        return installer.run()
