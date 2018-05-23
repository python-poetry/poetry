from .venv_command import VenvCommand


class InstallCommand(VenvCommand):
    """
    Installs the project dependencies.

    install
        { --no-dev : Do not install dev dependencies. }
        { --dry-run : Outputs the operations but will not execute anything
                      (implicitly enables --verbose). }
        { --E|extras=* : Extra sets of dependencies to install. }
    """

    help = """The <info>install</info> command reads the <comment>pyproject.toml</> file from
the current directory, processes it, and downloads and installs all the
libraries and dependencies outlined in that file. If the file does not
exist it will look for <comment>pyproject.toml</> and do the same.

<info>poetry install</info>    
"""

    _loggers = [
        'poetry.repositories.pypi_repository'
    ]

    def handle(self):
        from poetry.installation import Installer

        installer = Installer(
            self.output,
            self.venv,
            self.poetry.package,
            self.poetry.locker,
            self.poetry.pool
        )

        installer.extras(self.option('extras'))
        installer.dev_mode(not self.option('no-dev'))
        installer.dry_run(self.option('dry-run'))
        installer.verbose(self.option('verbose'))

        return installer.run()
