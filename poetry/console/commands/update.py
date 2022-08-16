from cleo import argument
from cleo import option

from .installer_command import InstallerCommand


class UpdateCommand(InstallerCommand):

    name = "update"
    description = (
        "Update the dependencies as according to the <comment>pyproject.toml</> file."
    )

    arguments = [
        argument("packages", "The packages to update", optional=True, multiple=True)
    ]
    options = [
        option("no-dev", None, "Do not update the development dependencies."),
        option(
            "dry-run",
            None,
            "Output the operations but do not execute anything "
            "(implicitly enables --verbose).",
        ),
        option("lock", None, "Do not perform operations (only update the lockfile)."),
    ]

    loggers = ["poetry.repositories.pypi_repository"]

    def handle(self):
        packages = self.argument("packages")

        self._installer.use_executor(
            self.poetry.config.get("experimental.new-installer", False)
        )

        if packages:
            self._installer.whitelist({name: "*" for name in packages})

        self._installer.dev_mode(not self.option("no-dev"))
        self._installer.dry_run(self.option("dry-run"))
        self._installer.execute_operations(not self.option("lock"))

        # Force update
        self._installer.update(True)

        return self._installer.run()
