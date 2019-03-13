from .env_command import EnvCommand


class LockCommand(EnvCommand):
    """
    Locks the project dependencies.

    lock
    """

    help = """The <info>lock</info> command reads the <comment>pyproject.toml</> file from
the current directory, processes it, and locks the depdencies in the <comment>poetry.lock</> file.

<info>poetry lock</info>
"""

    _loggers = ["poetry.repositories.pypi_repository"]

    def handle(self):
        from poetry.installation import Installer

        installer = Installer(
            self.output,
            self.env,
            self.poetry.package,
            self.poetry.locker,
            self.poetry.pool,
        )

        installer.lock()

        return installer.run()
