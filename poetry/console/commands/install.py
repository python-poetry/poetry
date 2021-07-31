from cleo.helpers import option

from .installer_command import InstallerCommand


class InstallCommand(InstallerCommand):

    name = "install"
    description = "Installs the project dependencies."

    options = [
        option(
            "without",
            None,
            "The dependency groups to ignore for installation.",
            flag=False,
            multiple=True,
        ),
        option(
            "with",
            None,
            "The optional dependency groups to include for installation.",
            flag=False,
            multiple=True,
        ),
        option("default", None, "Only install the default dependencies."),
        option(
            "only",
            None,
            "The only dependency groups to install.",
            flag=False,
            multiple=True,
        ),
        option(
            "no-dev",
            None,
            "Do not install the development dependencies. (<warning>Deprecated</warning>)",
        ),
        option(
            "dev-only",
            None,
            "Only install the development dependencies. (<warning>Deprecated</warning>)",
        ),
        option(
            "sync",
            None,
            "Synchronize the environment with the locked packages and the specified groups.",
        ),
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
            "remove-untracked",
            None,
            "Removes packages not present in the lock file.",
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

    _loggers = ["poetry.repositories.pypi_repository", "poetry.inspection.info"]

    def handle(self) -> int:
        from poetry.core.masonry.utils.module import ModuleOrPackageNotFound
        from poetry.masonry.builders import EditableBuilder

        self._installer.use_executor(
            self.poetry.config.get("experimental.new-installer", False)
        )

        extras = []
        for extra in self.option("extras"):
            if " " in extra:
                extras += [e.strip() for e in extra.split(" ")]
            else:
                extras.append(extra)

        self._installer.extras(extras)

        excluded_groups = []
        included_groups = []
        only_groups = []
        if self.option("no-dev"):
            self.line(
                "<warning>The `<fg=yellow;options=bold>--no-dev</>` option is deprecated,"
                "use the `<fg=yellow;options=bold>--without dev</>` notation instead.</warning>"
            )
            excluded_groups.append("dev")
        elif self.option("dev-only"):
            self.line(
                "<warning>The `<fg=yellow;options=bold>--dev-only</>` option is deprecated,"
                "use the `<fg=yellow;options=bold>--only dev</>` notation instead.</warning>"
            )
            only_groups.append("dev")

        excluded_groups.extend(
            [
                group.strip()
                for groups in self.option("without")
                for group in groups.split(",")
            ]
        )
        included_groups.extend(
            [
                group.strip()
                for groups in self.option("with")
                for group in groups.split(",")
            ]
        )
        only_groups.extend(
            [
                group.strip()
                for groups in self.option("only")
                for group in groups.split(",")
            ]
        )

        if self.option("default"):
            only_groups.append("default")

        with_synchronization = self.option("sync")
        if self.option("remove-untracked"):
            self.line(
                "<warning>The `<fg=yellow;options=bold>--remove-untracked</>` option is deprecated,"
                "use the `<fg=yellow;options=bold>--sync</>` option instead.</warning>"
            )

            with_synchronization = True

        self._installer.only_groups(only_groups)
        self._installer.without_groups(excluded_groups)
        self._installer.with_groups(included_groups)
        self._installer.dry_run(self.option("dry-run"))
        self._installer.requires_synchronization(with_synchronization)
        self._installer.verbose(self._io.is_verbose())

        return_code = self._installer.run()

        if return_code != 0:
            return return_code

        if self.option("no-root") or self.option("only"):
            return 0

        try:
            builder = EditableBuilder(self.poetry, self._env, self._io)
        except ModuleOrPackageNotFound:
            # This is likely due to the fact that the project is an application
            # not following the structure expected by Poetry
            # If this is a true error it will be picked up later by build anyway.
            return 0

        self.line("")
        if not self._io.output.is_decorated() or self.io.is_debug():
            self.line(
                "<b>Installing</> the current project: <c1>{}</c1> (<c2>{}</c2>)".format(
                    self.poetry.package.pretty_name, self.poetry.package.pretty_version
                )
            )
        else:
            self.write(
                "<b>Installing</> the current project: <c1>{}</c1> (<c2>{}</c2>)".format(
                    self.poetry.package.pretty_name, self.poetry.package.pretty_version
                )
            )

        if self.option("dry-run"):
            self.line("")
            return 0

        builder.build()

        if self._io.output.is_decorated() and not self.io.is_debug():
            self.overwrite(
                "<b>Installing</> the current project: <c1>{}</c1> (<success>{}</success>)".format(
                    self.poetry.package.pretty_name, self.poetry.package.pretty_version
                )
            )
            self.line("")

        return 0
