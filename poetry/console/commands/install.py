import os

from .env_command import EnvCommand


class InstallCommand(EnvCommand):
    """
    Installs the project dependencies.

    install
        { --no-dev : Do not install dev dependencies. }
        { --dry-run : Outputs the operations but will not execute anything
                      (implicitly enables --verbose). }
        { --E|extras=* : Extra sets of dependencies to install. }
        { --develop=* : Install given packages in development mode. }
    """

    help = """The <info>install</info> command reads the <comment>poetry.lock</> file from
the current directory, processes it, and downloads and installs all the
libraries and dependencies outlined in that file. If the file does not
exist it will look for <comment>pyproject.toml</> and do the same.

<info>poetry install</info>
"""

    _loggers = ["poetry.repositories.pypi_repository"]

    def handle(self):
        from poetry.installation import Installer
        from poetry.io import NullIO
        from poetry.masonry.builders import EditableBuilder
        from poetry.masonry.utils.module import ModuleOrPackageNotFound

        installer = Installer(
            self.output,
            self.env,
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

        return_code = installer.run()

        if return_code != 0:
            return return_code

        try:
            builder = EditableBuilder(self.poetry, self._env, NullIO())
        except ModuleOrPackageNotFound:
            # This is likely due to the fact that the project is an application
            # not following the structure expected by Poetry
            # If this is a true error it will be picked up later by build anyway.
            return 0

        self.line(
            "  - Installing <info>{}</info> (<comment>{}</comment>)".format(
                self.poetry.package.pretty_name, self.poetry.package.pretty_version
            )
        )

        if self.option("dry-run"):
            return 0

        builder.build()

        return 0
