from .venv_command import VenvCommand


class UpdateCommand(VenvCommand):
    """
    Update dependencies as according to the <comment>pyproject.toml</> file.

    update
        { packages?* : The packages to update. }
        { --no-dev : Do not install dev dependencies. }
        { --dry-run : Outputs the operations but will not execute anything
                      (implicitly enables --verbose). }
    """

    _loggers = ["poetry.repositories.pypi_repository"]

    def handle(self):
        from poetry.installation import Installer

        packages = self.argument("packages")

        installer = Installer(
            self.output,
            self.venv,
            self.poetry.package,
            self.poetry.locker,
            self.poetry.pool,
        )

        if packages:
            installer.whitelist({name: "*" for name in packages})

        installer.dev_mode(not self.option("no-dev"))
        installer.dry_run(self.option("dry-run"))

        # Force update
        installer.update(True)

        return installer.run()
