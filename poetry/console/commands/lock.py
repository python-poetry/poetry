from .installer_command import InstallerCommand


class LockCommand(InstallerCommand):

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
        self._installer.use_executor(
            self.poetry.config.get("experimental.new-installer", False)
        )

        self._installer.lock()

        return self._installer.run()
