from poetry.installation import Installer
from poetry.repositories.pypi_repository import PyPiRepository

from .command import Command


class UpdateCommand(Command):
    """
    Update dependencies as according to the <comment>poetry.toml</> file.

    update
        { packages?* : The packages to update. }
        { --no-dev : Do not install dev dependencies. }
        { --dry-run : Outputs the operations but will not execute anything
                      (implicitly enables --verbose). }
    """

    def handle(self):
        packages = self.argument('packages')

        installer = Installer(
            self.output,
            self.poetry.package,
            self.poetry.locker,
            self.poetry.pool
        )

        if packages:
            installer.whitelist({name: '*' for name in packages})

        installer.dev_mode(not self.option('no-dev'))
        installer.dry_run(self.option('dry-run'))

        # Force update
        installer.update(True)

        return installer.run()
