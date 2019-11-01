from cleo import argument
from cleo import option

from .env_command import EnvCommand


class UpdateCommand(EnvCommand):

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
        from poetry.installation.installer import Installer

        packages = self.argument("packages")

        installer = Installer(
            self.io, self.env, self.poetry.package, self.poetry.locker, self.poetry.pool
        )

        if packages:
            installer.whitelist({name: "*" for name in packages})

        installer.dev_mode(not self.option("no-dev"))
        installer.dry_run(self.option("dry-run"))
        installer.execute_operations(not self.option("lock"))

        # Force update
        installer.update(True)

        return installer.run()
