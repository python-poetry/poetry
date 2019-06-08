from cleo import argument
from cleo import option

from .init import InitCommand
from .env_command import EnvCommand


class AddCommand(EnvCommand, InitCommand):

    name = "add"
    description = "Add a new dependency to <comment>pyproject.toml</>."

    arguments = [argument("name", "Packages to add.", multiple=True)]
    options = [
        option("dev", "D", "Add package as development dependency."),
        option("git", None, "The url of the Git repository.", flag=False),
        option("path", None, "The path to a dependency.", flag=False),
        option(
            "extras",
            "E",
            "Extras to activate for the dependency.",
            flag=False,
            multiple=True,
        ),
        option("optional", None, "Add as an optional dependency."),
        option(
            "python",
            None,
            "Python version for which the dependencies must be installed.",
            flag=False,
        ),
        option(
            "platform",
            None,
            "Platforms for which the dependencies must be installed.",
            flag=False,
        ),
        option("allow-prereleases", None, "Accept prereleases."),
        option(
            "dry-run",
            None,
            "Outputs the operations but will not execute anything (implicitly enables --verbose).",
        ),
    ]

    help = """The add command adds required packages to your <comment>pyproject.toml</> and installs them.

If you do not specify a version constraint, poetry will choose a suitable one based on the available package versions.
"""

    loggers = ["poetry.repositories.pypi_repository"]

    def handle(self):
        from poetry.installation import Installer
        from poetry.semver import parse_constraint
        from tomlkit import inline_table

        packages = self.argument("name")
        is_dev = self.option("dev")

        if (self.option("git") or self.option("path") or self.option("extras")) and len(
            packages
        ) > 1:
            raise ValueError(
                "You can only specify one package "
                "when using the --git or --path options"
            )

        if self.option("git") and self.option("path"):
            raise RuntimeError("--git and --path cannot be used at the same time")

        section = "dependencies"
        if is_dev:
            section = "dev-dependencies"

        original_content = self.poetry.file.read()
        content = self.poetry.file.read()
        poetry_content = content["tool"]["poetry"]

        if section not in poetry_content:
            poetry_content[section] = {}

        for name in packages:
            for key in poetry_content[section]:
                if key.lower() == name.lower():
                    raise ValueError("Package {} is already present".format(name))

        if self.option("git") or self.option("path"):
            requirements = {packages[0]: ""}
        else:
            requirements = self._determine_requirements(
                packages, allow_prereleases=self.option("allow-prereleases")
            )
            requirements = self._format_requirements(requirements)

            # validate requirements format
            for constraint in requirements.values():
                parse_constraint(constraint)

        for name, _constraint in requirements.items():
            constraint = inline_table()
            constraint["version"] = _constraint

            if self.option("git"):
                del constraint["version"]

                constraint["git"] = self.option("git")
            elif self.option("path"):
                del constraint["version"]

                constraint["path"] = self.option("path")

            if self.option("optional"):
                constraint["optional"] = True

            if self.option("allow-prereleases"):
                constraint["allows-prereleases"] = True

            if self.option("extras"):
                extras = []
                for extra in self.option("extras"):
                    if " " in extra:
                        extras += [e.strip() for e in extra.split(" ")]
                    else:
                        extras.append(extra)

                constraint["extras"] = self.option("extras")

            if self.option("python"):
                constraint["python"] = self.option("python")

            if self.option("platform"):
                constraint["platform"] = self.option("platform")

            if len(constraint) == 1 and "version" in constraint:
                constraint = constraint["version"]

            poetry_content[section][name] = constraint

        # Write new content
        self.poetry.file.write(content)

        # Cosmetic new line
        self.line("")

        # Update packages
        self.reset_poetry()

        installer = Installer(
            self.io, self.env, self.poetry.package, self.poetry.locker, self.poetry.pool
        )

        installer.dry_run(self.option("dry-run"))
        installer.update(True)
        installer.whitelist(requirements)

        try:
            status = installer.run()
        except Exception:
            self.poetry.file.write(original_content)

            raise

        if status != 0 or self.option("dry-run"):
            # Revert changes
            if not self.option("dry-run"):
                self.error(
                    "\n"
                    "Addition failed, reverting pyproject.toml "
                    "to its original content."
                )

            self.poetry.file.write(original_content)

        return status
