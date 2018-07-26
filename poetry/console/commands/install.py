from .venv_command import VenvCommand


class InstallCommand(VenvCommand):
    """
    Installs the project dependencies.

    install
        { --no-dev : Do not install dev dependencies. }
        { --dry-run : Outputs the operations but will not execute anything
                      (implicitly enables --verbose). }
        { --E|extras=* : Extra sets of dependencies to install. }
        { --develop=* : Install given packages in development mode. }
    """

    help = """The <info>install</info> command reads the <comment>pyproject.lock</> file from
the current directory, processes it, and downloads and installs all the
libraries and dependencies outlined in that file. If the file does not
exist it will look for <comment>pyproject.toml</> and do the same.

<info>poetry install</info>
"""

    _loggers = ["poetry.repositories.pypi_repository"]

    def handle(self):
        from poetry.installation import Installer

        installer = Installer(
            self.output,
            self.venv,
            self.poetry.package,
            self.poetry.locker,
            self.poetry.pool,
        )

        extras = []
        for extra in self.option("extras"):
            if " " in extra:
                extras += [e.strip() for e in extra.split(" ")]
            else:
                extras.append(extra)

        installer.extras(extras)
        installer.dev_mode(not self.option("no-dev"))
        installer.develop(self.option("develop"))
        installer.dry_run(self.option("dry-run"))
        installer.verbose(self.option("verbose"))

        return installer.run()
