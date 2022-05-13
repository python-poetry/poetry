from __future__ import annotations

from cleo.helpers import option

from poetry.console.commands.installer_command import InstallerCommand


class InstallCommand(InstallerCommand):

    name = "install"
    description = "Installs the project dependencies."

    options = [
        *InstallerCommand._group_dependency_options(),
        option(
            "no-dev",
            None,
            "Do not install the development dependencies."
            " (<warning>Deprecated</warning>)",
        ),
        option(
            "dev-only",
            None,
            "Only install the development dependencies."
            " (<warning>Deprecated</warning>)",
        ),
        option(
            "sync",
            None,
            "Synchronize the environment with the locked packages and the specified"
            " groups.",
        ),
        option(
            "no-root", None, "Do not install the root package (the current project)."
        ),
        option(
            "no-binary",
            None,
            "Do not use binary distributions for packages matching given policy.\n"
            "Use package name to disallow a specific package; or <b>:all:</b> to\n"
            "disallow and <b>:none:</b> to force binary for all packages. Multiple\n"
            "packages can be specified separated by commas.",
            flag=False,
            multiple=True,
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
            "Removes packages not present in the lock file."
            " (<warning>Deprecated</warning>)",
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

        from poetry.masonry.builders.editable import EditableBuilder

        self._installer.use_executor(
            self.poetry.config.get("experimental.new-installer", False)
        )

        extras = []
        for extra in self.option("extras", []):
            if " " in extra:
                extras += [e.strip() for e in extra.split(" ")]
            else:
                extras.append(extra)

        self._installer.extras(extras)

        with_synchronization = self.option("sync")
        if self.option("remove-untracked"):
            self.line_error(
                "<warning>The `<fg=yellow;options=bold>--remove-untracked</>` option is"
                " deprecated, use the `<fg=yellow;options=bold>--sync</>` option"
                " instead.</warning>"
            )

            with_synchronization = True

        if self.option("no-binary"):
            policy = ",".join(self.option("no-binary", []))
            try:
                self._installer.no_binary(policy=policy)
            except ValueError as e:
                self.line_error(
                    f"<warning>Invalid value (<c1>{policy}</>) for"
                    f" `<b>--no-binary</b>`</>.\n\n<error>{e}</>"
                )
                return 1

        self._installer.only_groups(self.activated_groups)
        self._installer.dry_run(self.option("dry-run"))
        self._installer.requires_synchronization(with_synchronization)
        self._installer.verbose(self._io.is_verbose())

        return_code = self._installer.run()

        if return_code != 0:
            return return_code

        if self.option("no-root"):
            return 0

        try:
            builder = EditableBuilder(self.poetry, self._env, self._io)
        except ModuleOrPackageNotFound:
            # This is likely due to the fact that the project is an application
            # not following the structure expected by Poetry
            # If this is a true error it will be picked up later by build anyway.
            return 0

        log_install = (
            "<b>Installing</> the current project:"
            f" <c1>{self.poetry.package.pretty_name}</c1>"
            f" (<{{tag}}>{self.poetry.package.pretty_version}</>)"
        )
        overwrite = self._io.output.is_decorated() and not self.io.is_debug()
        self.line("")
        self.write(log_install.format(tag="c2"))
        if not overwrite:
            self.line("")

        if self.option("dry-run"):
            self.line("")
            return 0

        builder.build()

        if overwrite:
            self.overwrite(log_install.format(tag="success"))
            self.line("")

        return 0
