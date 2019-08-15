from .env_command import EnvCommand


class UpdateCommand(EnvCommand):
    """
    Update dependencies as according to the <comment>pyproject.toml</> file.

    update
        { packages?* : The packages to update. }
        { --no-dev : Do not install dev dependencies. }
        { --dry-run : Outputs the operations but will not execute anything
                      (implicitly enables --verbose). }
        { --lock : Do not perform install (only update the lockfile). }
    """

    _loggers = ["poetry.repositories.pypi_repository"]

    def handle(self):
        from poetry.installation import Installer

        packages = self.argument("packages")

        installer = Installer(
            self.output,
            self.env,
            self.poetry.package,
            self.poetry.locker,
            self.poetry.pool,
        )

        if packages:
            installer.whitelist({name: "*" for name in packages})

        installer.dev_mode(not self.option("no-dev"))
        installer.dry_run(self.option("dry-run"))
        installer.execute_operations(not self.option("lock"))

        # Force update
        installer.update(True)

        return installer.run()
