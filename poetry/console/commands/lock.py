from .env_command import EnvCommand


class LockCommand(EnvCommand):

    name = "lock"
    description = "Locks the project dependencies."

    help = """
The <info>lock</info> command reads the <comment>pyproject.toml</> file from the
current directory, processes it, and locks the dependencies in the <comment>poetry.lock</>
file.

<info>poetry lock</info>
"""

    loggers = ["poetry.repositories.pypi_repository"]

    def handle(self):
        from poetry.installation.installer import Installer

        installer = Installer(
            self.io, self.env, self.poetry.package, self.poetry.locker, self.poetry.pool
        )

        installer.lock()

        return installer.run()
