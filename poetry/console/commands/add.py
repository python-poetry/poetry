# -*- coding: utf-8 -*-
from typing import Dict
from typing import List

from cleo import argument
from cleo import option

from .init import InitCommand
from .installer_command import InstallerCommand


class AddCommand(InstallerCommand, InitCommand):

    name = "add"
    description = "Adds a new dependency to <comment>pyproject.toml</>."

    arguments = [argument("name", "The packages to add.", multiple=True)]
    options = [
        option("dev", "D", "Add as a development dependency."),
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
            "Python version for which the dependency must be installed.",
            flag=False,
        ),
        option(
            "platform",
            None,
            "Platforms for which the dependency must be installed.",
            flag=False,
        ),
        option(
            "source",
            None,
            "Name of the source to use to install the package.",
            flag=False,
        ),
        option("allow-prereleases", None, "Accept prereleases."),
        option(
            "dry-run",
            None,
            "Output the operations but do not execute anything (implicitly enables --verbose).",
        ),
        option("lock", None, "Do not perform operations (only update the lockfile)."),
    ]
    help = (
        "The add command adds required packages to your <comment>pyproject.toml</> and installs them.\n\n"
        "If you do not specify a version constraint, poetry will choose a suitable one based on the available package versions.\n\n"
        "You can specify a package in the following forms:\n"
        "  - A single name (<b>requests</b>)\n"
        "  - A name and a constraint (<b>requests@^2.23.0</b>)\n"
        "  - A git url (<b>git+https://github.com/python-poetry/poetry.git</b>)\n"
        "  - A git url with a revision (<b>git+https://github.com/python-poetry/poetry.git#develop</b>)\n"
        "  - A file path (<b>../my-package/my-package.whl</b>)\n"
        "  - A directory (<b>../my-package/</b>)\n"
        "  - A url (<b>https://example.com/packages/my-package-0.1.0.tar.gz</b>)\n"
    )

    loggers = ["poetry.repositories.pypi_repository", "poetry.inspection.info"]

    def handle(self):
        from tomlkit import inline_table

        from poetry.core.semver import parse_constraint

        packages = self.argument("name")
        is_dev = self.option("dev")

        if self.option("extras") and len(packages) > 1:
            raise ValueError(
                "You can only specify one package " "when using the --extras option"
            )

        section = "dependencies"
        if is_dev:
            section = "dev-dependencies"

        original_content = self.poetry.file.read()
        content = self.poetry.file.read()
        poetry_content = content["tool"]["poetry"]

        if section not in poetry_content:
            poetry_content[section] = {}

        existing_packages = self.get_existing_packages_from_input(
            packages, poetry_content, section
        )

        if existing_packages:
            self.notify_about_existing_packages(existing_packages)

        packages = [name for name in packages if name not in existing_packages]

        if not packages:
            self.poetry.file.write(content)
            self.line("Nothing to add.")
            return 0

        requirements = self._determine_requirements(
            packages,
            allow_prereleases=self.option("allow-prereleases"),
            source=self.option("source"),
        )

        for _constraint in requirements:
            if "version" in _constraint:
                # Validate version constraint
                parse_constraint(_constraint["version"])

            constraint = inline_table()
            for name, value in _constraint.items():
                if name == "name":
                    continue

                constraint[name] = value

            if self.option("optional"):
                constraint["optional"] = True

            if self.option("allow-prereleases"):
                constraint["allow-prereleases"] = True

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

            if self.option("source"):
                constraint["source"] = self.option("source")

            if len(constraint) == 1 and "version" in constraint:
                constraint = constraint["version"]

            poetry_content[section][_constraint["name"]] = constraint

        # Write new content
        self.poetry.file.write(content)

        # Cosmetic new line
        self.line("")

        # Update packages
        self.reset_poetry()

        self._installer.set_package(self.poetry.package)
        self._installer.dry_run(self.option("dry-run"))
        self._installer.verbose(self._io.is_verbose())
        self._installer.update(True)
        if self.option("lock"):
            self._installer.lock()

        self._installer.whitelist([r["name"] for r in requirements])

        try:
            status = self._installer.run()
        except Exception:
            self.poetry.file.write(original_content)

            raise

        if status != 0 or self.option("dry-run"):
            # Revert changes
            if not self.option("dry-run"):
                self.line_error(
                    "\n"
                    "<error>Failed to add packages, reverting the pyproject.toml file "
                    "to its original content.</error>"
                )

            self.poetry.file.write(original_content)

        return status

    def get_existing_packages_from_input(
        self, packages, poetry_content, target_section
    ):  # type: (List[str], Dict, str) -> List[str]
        existing_packages = []

        for name in packages:
            for key in poetry_content[target_section]:
                if key.lower() == name.lower():
                    existing_packages.append(name)

        return existing_packages

    def notify_about_existing_packages(
        self, existing_packages
    ):  # type: (List[str]) -> None
        self.line(
            "The following packages are already present in the pyproject.toml and will be skipped:\n"
        )
        for name in existing_packages:
            self.line("  • <c1>{name}</c1>".format(name=name))
        self.line(
            "\nIf you want to update it to the latest compatible version, you can use `poetry update package`.\n"
            "If you prefer to upgrade it to the latest available version, you can use `poetry add package@latest`.\n"
        )
