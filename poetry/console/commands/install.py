from poetry.installation import Installer
from poetry.repositories.pypi_repository import PyPiRepository

from .command import Command


class InstallCommand(Command):
    """
    Installs the project dependencies.

    install
        { --no-dev : Do not install dev dependencies. }
        { --dry-run : Outputs the operations but will not execute anything
                      (implicitly enables --verbose). }
    """

    help = """The <info>install</info> command reads the <comment>poetry.lock</> file from
the current directory, processes it, and downloads and installs all the
libraries and dependencies outlined in that file. If the file does not
exist it will look for <comment>poetry.toml</> and do the same.

<info>poetry install</info>    
"""

    def handle(self):
        installer = Installer(
            self.output,
            self.poetry.package,
            self.poetry.locker,
            self.poetry.pool
        )

        installer.dev_mode(not self.option('no-dev'))
        installer.dry_run(self.option('dry-run'))

        return installer.run()
