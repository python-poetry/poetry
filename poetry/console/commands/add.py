from typing import Dict
from typing import List

from cleo.helpers import argument
from cleo.helpers import option

from .init import InitCommand
from .installer_command import InstallerCommand


class AddCommand(InstallerCommand, InitCommand):

    name = "add"
    description = "Adds a new dependency to <comment>pyproject.toml</>."

    arguments = [argument("name", "The packages to add.", multiple=True)]
    options = [
        option(
            "group",
            "-G",
            "The group to add the dependency to.",
            flag=False,
            default="default",
        ),
        option("dev", "D", "Add as a development dependency."),
        option("editable", "e", "Add vcs/path dependencies as editable."),
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
        "  - A git SSH url (<b>git+ssh://github.com/python-poetry/poetry.git</b>)\n"
        "  - A git SSH url with a revision (<b>git+ssh://github.com/python-poetry/poetry.git#develop</b>)\n"
        "  - A file path (<b>../my-package/my-package.whl</b>)\n"
        "  - A directory (<b>../my-package/</b>)\n"
        "  - A url (<b>https://example.com/packages/my-package-0.1.0.tar.gz</b>)\n"
    )

    loggers = ["poetry.repositories.pypi_repository", "poetry.inspection.info"]

    def handle(self) -> int:
        from tomlkit import inline_table
        from tomlkit import parse as parse_toml
        from tomlkit import table

        from poetry.core.semver.helpers import parse_constraint
        from poetry.factory import Factory

        packages = self.argument("name")
        if self.option("dev"):
            self.line(
                "<warning>The --dev option is deprecated, "
                "use the `--group dev` notation instead.</warning>"
            )
            self.line("")
            group = "dev"
        else:
            group = self.option("group")

        if self.option("extras") and len(packages) > 1:
            raise ValueError(
                "You can only specify one package when using the --extras option"
            )

        content = self.poetry.file.read()
        poetry_content = content["tool"]["poetry"]

        if group == "default":
            if "dependencies" not in poetry_content:
                poetry_content["dependencies"] = table()

            section = poetry_content["dependencies"]
        else:
            if "group" not in poetry_content:
                group_table = table()
                group_table._is_super_table = True
                poetry_content.value._insert_after("dependencies", "group", group_table)

            groups = poetry_content["group"]
            if group not in groups:
                group_table = parse_toml(
                    f"[tool.poetry.group.{group}.dependencies]\n\n"
                )["tool"]["poetry"]["group"][group]
                poetry_content["group"][group] = group_table

            if "dependencies" not in poetry_content["group"][group]:
                poetry_content["group"][group]["dependencies"] = table()

            section = poetry_content["group"][group]["dependencies"]

        existing_packages = self.get_existing_packages_from_input(packages, section)

        if existing_packages:
            self.notify_about_existing_packages(existing_packages)

        packages = [name for name in packages if name not in existing_packages]

        if not packages:
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

            if self.option("editable"):
                if "git" in _constraint or "path" in _constraint:
                    constraint["develop"] = True
                else:
                    self.line_error(
                        "\n"
                        "<error>Failed to add packages. "
                        "Only vcs/path dependencies support editable installs. "
                        f"<c1>{_constraint['name']}</c1> is neither."
                    )
                    self.line_error("\nNo changes were applied.")
                    return 1

            if self.option("python"):
                constraint["python"] = self.option("python")

            if self.option("platform"):
                constraint["platform"] = self.option("platform")

            if self.option("source"):
                constraint["source"] = self.option("source")

            if len(constraint) == 1 and "version" in constraint:
                constraint = constraint["version"]

            section[_constraint["name"]] = constraint
            self.poetry.package.add_dependency(
                Factory.create_dependency(
                    _constraint["name"],
                    constraint,
                    groups=[group],
                    root_dir=self.poetry.file.parent,
                )
            )

        # Refresh the locker
        self.poetry.set_locker(
            self.poetry.locker.__class__(self.poetry.locker.lock.path, poetry_content)
        )
        self._installer.set_locker(self.poetry.locker)

        # Cosmetic new line
        self.line("")

        self._installer.set_package(self.poetry.package)
        self._installer.dry_run(self.option("dry-run"))
        self._installer.verbose(self._io.is_verbose())
        self._installer.update(True)
        if self.option("lock"):
            self._installer.lock()

        self._installer.whitelist([r["name"] for r in requirements])

        status = self._installer.run()

        if status == 0 and not self.option("dry-run"):
            self.poetry.file.write(content)

        return status

    def get_existing_packages_from_input(
        self, packages: List[str], section: Dict
    ) -> List[str]:
        existing_packages = []

        for name in packages:
            for key in section:
                if key.lower() == name.lower():
                    existing_packages.append(name)

        return existing_packages

    def notify_about_existing_packages(self, existing_packages: List[str]) -> None:
        self.line(
            "The following packages are already present in the pyproject.toml and will be skipped:\n"
        )
        for name in existing_packages:
            self.line("  • <c1>{name}</c1>".format(name=name))
        self.line(
            "\nIf you want to update it to the latest compatible version, you can use `poetry update package`.\n"
            "If you prefer to upgrade it to the latest available version, you can use `poetry add package@latest`.\n"
        )
