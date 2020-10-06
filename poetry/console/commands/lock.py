from cleo import option

from .installer_command import InstallerCommand


class LockCommand(InstallerCommand):

    name = "lock"
    description = "Locks the project dependencies."

    options = [
        option(
            "no-update", None, "Do not update locked versions, only refresh lock file."
        ),
        option(
            "check",
            description="Check if the <comment>lock</> file is up to "
            "date with <comment>pyproject.toml</>",
        ),
    ]

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
        if self.option("check"):
            if not self.poetry.locker.is_locked():
                return 3
            if not self.poetry.locker.is_fresh():
                return 5
            return 0

        self._installer.lock(update=not self.option("no-update"))

        return self._installer.run()
