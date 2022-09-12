from __future__ import annotations

import sys

from typing import TYPE_CHECKING
from typing import Any

from cleo.helpers import option
from packaging.utils import canonicalize_name

from poetry.console.commands.command import Command
from poetry.console.commands.env_command import EnvCommand
from poetry.utils.requirements import determine_requirements_from_list
from poetry.utils.requirements import find_best_version_for_package
from poetry.utils.requirements import format_requirements
from poetry.utils.requirements import parse_requirements


if TYPE_CHECKING:
    from packaging.utils import NormalizedName
    from poetry.core.packages.package import Package

    from poetry.repositories import Pool
    from poetry.utils.requirements import Requirements


class InitCommand(Command):
    name = "init"
    description = (
        "Creates a basic <comment>pyproject.toml</> file in the current directory."
    )

    options = [
        option("name", None, "Name of the package.", flag=False),
        option("description", None, "Description of the package.", flag=False),
        option("author", None, "Author name of the package.", flag=False),
        option("python", None, "Compatible Python versions.", flag=False),
        option(
            "dependency",
            None,
            "Package to require, with an optional version constraint, "
            "e.g. requests:^2.10.0 or requests=2.11.1.",
            flag=False,
            multiple=True,
        ),
        option(
            "dev-dependency",
            None,
            "Package to require for development, with an optional version constraint, "
            "e.g. requests:^2.10.0 or requests=2.11.1.",
            flag=False,
            multiple=True,
        ),
        option("license", "License of the package.", flag=False),
    ]

    help = """\
The <c1>init</c1> command creates a basic <comment>pyproject.toml</> file in the\
 current directory.
"""

    def __init__(self) -> None:
        super().__init__()

        self._pool: Pool | None = None

    def handle(self) -> int:
        from pathlib import Path

        from poetry.core.pyproject.toml import PyProjectTOML
        from poetry.core.vcs.git import GitConfig

        from poetry.layouts import layout
        from poetry.utils.env import SystemEnv

        pyproject = PyProjectTOML(Path.cwd() / "pyproject.toml")

        if pyproject.file.exists():
            if pyproject.is_poetry_project():
                self.line_error(
                    "<error>A pyproject.toml file with a poetry section already"
                    " exists.</error>"
                )
                return 1

            if pyproject.data.get("build-system"):
                self.line_error(
                    "<error>A pyproject.toml file with a defined build-system already"
                    " exists.</error>"
                )
                return 1

        vcs_config = GitConfig()

        if self.io.is_interactive():
            self.line("")
            self.line(
                "This command will guide you through creating your"
                " <info>pyproject.toml</> config."
            )
            self.line("")

        name = self.option("name")
        if not name:
            name = Path.cwd().name.lower()

            question = self.create_question(
                f"Package name [<comment>{name}</comment>]: ", default=name
            )
            name = self.ask(question)

        version = "0.1.0"
        question = self.create_question(
            f"Version [<comment>{version}</comment>]: ", default=version
        )
        version = self.ask(question)

        description = self.option("description")
        if not description:
            description = self.ask(self.create_question("Description []: ", default=""))

        author = self.option("author")
        if not author and vcs_config.get("user.name"):
            author = vcs_config["user.name"]
            author_email = vcs_config.get("user.email")
            if author_email:
                author += f" <{author_email}>"

        question = self.create_question(
            f"Author [<comment>{author}</comment>, n to skip]: ", default=author
        )
        question.set_validator(lambda v: self._validate_author(v, author))
        author = self.ask(question)

        if not author:
            authors = []
        else:
            authors = [author]

        license = self.option("license")
        if not license:
            license = self.ask(self.create_question("License []: ", default=""))

        python = self.option("python")
        if not python:
            current_env = SystemEnv(Path(sys.executable))
            default_python = "^" + ".".join(
                str(v) for v in current_env.version_info[:2]
            )
            question = self.create_question(
                f"Compatible Python versions [<comment>{default_python}</comment>]: ",
                default=default_python,
            )
            python = self.ask(question)

        if self.io.is_interactive():
            self.line("")

        requirements: Requirements = {}
        if self.option("dependency"):
            requirements = format_requirements(
                self._determine_requirements(self.option("dependency"))
            )

        question = "Would you like to define your main dependencies interactively?"
        help_message = """\
You can specify a package in the following forms:
  - A single name (<b>requests</b>): this will search for matches on PyPI
  - A name and a constraint (<b>requests@^2.23.0</b>)
  - A git url (<b>git+https://github.com/python-poetry/poetry.git</b>)
  - A git url with a revision\
 (<b>git+https://github.com/python-poetry/poetry.git#develop</b>)
  - A file path (<b>../my-package/my-package.whl</b>)
  - A directory (<b>../my-package/</b>)
  - A url (<b>https://example.com/packages/my-package-0.1.0.tar.gz</b>)
"""

        help_displayed = False
        if self.confirm(question, True):
            if self.io.is_interactive():
                self.line(help_message)
                help_displayed = True
            requirements.update(format_requirements(self._determine_requirements([])))
            if self.io.is_interactive():
                self.line("")

        dev_requirements: Requirements = {}
        if self.option("dev-dependency"):
            dev_requirements = format_requirements(
                self._determine_requirements(self.option("dev-dependency"))
            )

        question = (
            "Would you like to define your development dependencies interactively?"
        )
        if self.confirm(question, True):
            if self.io.is_interactive() and not help_displayed:
                self.line(help_message)

            dev_requirements.update(
                format_requirements(self._determine_requirements([]))
            )
            if self.io.is_interactive():
                self.line("")

        layout_ = layout("standard")(
            name,
            version,
            description=description,
            author=authors[0] if authors else None,
            license=license,
            python=python,
            dependencies=requirements,
            dev_dependencies=dev_requirements,
        )

        content = layout_.generate_poetry_content()
        for section in content:
            pyproject.data.append(section, content[section])
        if self.io.is_interactive():
            self.line("<info>Generated file</info>")
            self.line("")
            self.line(pyproject.data.as_string().replace("\r\n", "\n"))
            self.line("")

        if not self.confirm("Do you confirm generation?", True):
            self.line_error("<error>Command aborted</error>")

            return 1

        pyproject.save()

        return 0

    def _generate_choice_list(
        self, matches: list[Package], canonicalized_name: NormalizedName
    ) -> list[str]:
        choices = []
        matches_names = [p.name for p in matches]
        exact_match = canonicalized_name in matches_names
        if exact_match:
            choices.append(matches[matches_names.index(canonicalized_name)].pretty_name)

        for found_package in matches:
            if len(choices) >= 10:
                break

            if found_package.name == canonicalized_name:
                continue

            choices.append(found_package.pretty_name)

        return choices

    def _determine_requirements_interactive(self) -> list[dict[str, Any]]:
        result = []

        question = self.create_question(
            "Package to add or search for (leave blank to skip):"
        )
        question.set_validator(self._validate_package)

        package = self.ask(question)
        while package:
            constraint = parse_requirements([package], self, None)[0]
            if (
                "git" in constraint
                or "url" in constraint
                or "path" in constraint
                or "version" in constraint
            ):
                self.line(f"Adding <info>{package}</info>")
                result.append(constraint)
                package = self.ask("\nAdd a package:")
                continue

            canonicalized_name = canonicalize_name(constraint["name"])
            matches = self._get_pool().search(canonicalized_name)
            if not matches:
                self.line_error("<error>Unable to find package</error>")
                package = False
            else:
                choices = self._generate_choice_list(matches, canonicalized_name)

                info_string = (
                    f"Found <info>{len(matches)}</info> packages matching"
                    f" <c1>{package}</c1>"
                )

                if len(matches) > 10:
                    info_string += "\nShowing the first 10 matches"

                self.line(info_string)

                # Default to an empty value to signal no package was selected
                choices.append("")

                package = self.choice(
                    "\nEnter package # to add, or the complete package name if it"
                    " is not listed",
                    choices,
                    attempts=3,
                    default=len(choices) - 1,
                )

                if not package:
                    self.line("<warning>No package selected</warning>")

                # package selected by user, set constraint name to package name
                if package:
                    constraint["name"] = package

            # no constraint yet, determine the best version automatically
            if package and "version" not in constraint:
                question = self.create_question(
                    "Enter the version constraint to require "
                    "(or leave blank to use the latest version):"
                )
                question.attempts = 3
                question.validator = lambda x: (x or "").strip() or False

                package_constraint = self.ask(question)

                if package_constraint is None:
                    _, package_constraint = find_best_version_for_package(
                        self._get_pool(), package
                    )

                    self.line(
                        f"Using version <b>{package_constraint}</b> for"
                        f" <c1>{package}</c1>"
                    )

                constraint["version"] = package_constraint

            if package:
                result.append(constraint)

            if self.io.is_interactive():
                package = self.ask("\nAdd a package (leave blank to skip):")

        return result

    def _determine_requirements(
        self,
        requires: list[str],
        allow_prereleases: bool = False,
        source: str | None = None,
    ) -> list[dict[str, Any]]:
        if not requires:
            return self._determine_requirements_interactive()
        else:
            return determine_requirements_from_list(
                self, self._get_pool(), requires, allow_prereleases, source
            )

    def _validate_author(self, author: str, default: str) -> str | None:
        from poetry.core.packages.package import AUTHOR_REGEX

        author = author or default

        if author in ["n", "no"]:
            return None

        m = AUTHOR_REGEX.match(author)
        if not m:
            raise ValueError(
                "Invalid author string. Must be in the format: "
                "John Smith <john@example.com>"
            )

        return author

    @staticmethod
    def _validate_package(package: str | None) -> str | None:
        if package and len(package.split()) > 2:
            raise ValueError("Invalid package definition.")

        return package

    def _get_pool(self) -> Pool:
        from poetry.repositories import Pool
        from poetry.repositories.pypi_repository import PyPiRepository

        if isinstance(self, EnvCommand):
            return self.poetry.pool

        if self._pool is None:
            self._pool = Pool()
            self._pool.add_repository(PyPiRepository())

        return self._pool
