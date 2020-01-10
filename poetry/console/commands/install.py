from cleo import option

from .env_command import EnvCommand


class InstallCommand(EnvCommand):

    name = "install"
    description = "Installs the project dependencies."

    options = [
        option("no-dev", None, "Do not install the development dependencies."),
        option(
            "no-root", None, "Do not install the root package (the current project)."
        ),
        option(
            "dry-run",
            None,
            "Output the operations but do not execute anything "
            "(implicitly enables --verbose).",
        ),
        option(
            "extras",
            "E",
            "Extra sets of dependencies to install.",
            flag=False,
            multiple=True,
        ),
    ]

    help = """The <info>install</info> command reads the <comment>poetry.lock</> file from
the current directory, processes it, and downloads and installs all the
libraries and dependencies outlined in that file. If the file does not
exist it will look for <comment>pyproject.toml</> and do the same.

<info>poetry install</info>

By default, the above command will also install the current project. To install only the
dependencies and not including the current project, run the command with the
<info>--no-root</info> option like below:

<info> poetry install --no-root</info>
"""

    _loggers = ["poetry.repositories.pypi_repository"]

    def handle(self):
        from clikit.io import NullIO
        from poetry.installation.installer import Installer
        from poetry.masonry.builders import EditableBuilder
        from poetry.masonry.utils.module import ModuleOrPackageNotFound

        installer = Installer(
            self.io, self.env, self.poetry.package, self.poetry.locker, self.poetry.pool
        )

        extras = []
        for extra in self.option("extras"):
            if " " in extra:
                extras += [e.strip() for e in extra.split(" ")]
            else:
                extras.append(extra)

        installer.extras(extras)
        installer.dev_mode(not self.option("no-dev"))
        installer.dry_run(self.option("dry-run"))
        installer.verbose(self.option("verbose"))

        return_code = installer.run()

        if return_code != 0:
            return return_code

        if self.option("no-root"):
            return 0

        try:
            builder = EditableBuilder(self.poetry, self._env, NullIO())
        except ModuleOrPackageNotFound:
            # This is likely due to the fact that the project is an application
            # not following the structure expected by Poetry
            # If this is a true error it will be picked up later by build anyway.
            return 0

        self.line(
            "  - Installing <c1>{}</c1> (<b>{}</b>)".format(
                self.poetry.package.pretty_name, self.poetry.package.pretty_version
            )
        )

        if self.option("dry-run"):
            return 0

        builder.build()

        return 0
