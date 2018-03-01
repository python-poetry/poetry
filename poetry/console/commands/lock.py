from poetry.installation import Installer
from poetry.repositories.pypi_repository import PyPiRepository

from .command import Command


class LockCommand(Command):
    """
    Locks the project dependencies.

    lock
        { --no-dev : Do not install dev dependencies. }
    """

    help = """The <info>lock</info> command reads the <comment>poetry.toml</> file from
the current directory, processes it, and locks the depdencies in the <comment>poetry.lock</> file.

<info>poetry lock</info>    
"""

    def handle(self):
        installer = Installer(
            self.output,
            self.poetry.package,
            self.poetry.locker,
            self.poetry.pool
        )

        installer.update(True)
        installer.execute_operations(False)

        return installer.run()
