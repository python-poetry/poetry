# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from typing import List
from typing import Tuple

from .command import Command
from .env_command import EnvCommand


class InitCommand(Command):
    """
    Creates a basic <comment>pyproject.toml</> file in the current directory.

    init
        {--name= : Name of the package}
        {--description= : Description of the package}
        {--author= : Author name of the package}
        {--dependency=* : Package to require with an optional version constraint,
                          e.g. requests:^2.10.0 or requests=2.11.1}
        {--dev-dependency=* : Package to require for development with an optional version constraint,
                              e.g. requests:^2.10.0 or requests=2.11.1}
        {--l|license= : License of the package}
    """

    help = """\
The <info>init</info> command creates a basic <comment>pyproject.toml</> file in the current directory.
"""

    def __init__(self):
        super(InitCommand, self).__init__()

        self._pool = None

    def handle(self):
        from poetry.layouts import layout
        from poetry.utils._compat import Path
        from poetry.utils.env import Env
        from poetry.vcs.git import GitConfig

        if (Path.cwd() / "pyproject.toml").exists():
            self.error("A pyproject.toml file already exists.")
            return 1

        vcs_config = GitConfig()

        self.line(
            [
                "",
                "This command will guide you through creating your <info>pyproject.toml</> config.",
                "",
            ]
        )

        name = self.option("name")
        if not name:
            name = Path.cwd().name.lower()

            question = self.create_question(
                "Package name [<comment>{}</comment>]: ".format(name), default=name
            )
            name = self.ask(question)

        version = "0.1.0"
        question = self.create_question(
            "Version [<comment>{}</comment>]: ".format(version), default=version
        )
        version = self.ask(question)

        description = self.option("description") or ""
        question = self.create_question(
            "Description [<comment>{}</comment>]: ".format(description),
            default=description,
        )
        description = self.ask(question)

        author = self.option("author")
        if not author and vcs_config and vcs_config.get("user.name"):
            author = vcs_config["user.name"]
            author_email = vcs_config.get("user.email")
            if author_email:
                author += " <{}>".format(author_email)

        question = self.create_question(
            "Author [<comment>{}</comment>, n to skip]: ".format(author), default=author
        )
        question.validator = lambda v: self._validate_author(v, author)
        author = self.ask(question)

        if not author:
            authors = []
        else:
            authors = [author]

        license = self.option("license") or ""

        question = self.create_question(
            "License [<comment>{}</comment>]: ".format(license), default=license
        )
        question.validator = self._validate_license
        license = self.ask(question)

        current_env = Env.get(Path.cwd())
        default_python = "^{}".format(
            ".".join(str(v) for v in current_env.version_info[:2])
        )
        question = self.create_question(
            "Compatible Python versions [<comment>{}</comment>]: ".format(
                default_python
            ),
            default=default_python,
        )
        python = self.ask(question)

        self.line("")

        requirements = {}

        question = (
            "Would you like to define your dependencies" " (require) interactively?"
        )
        if self.confirm(question, True):
            requirements = self._format_requirements(
                self._determine_requirements(self.option("dependency"))
            )

        dev_requirements = {}

        question = (
            "Would you like to define your dev dependencies"
            " (require-dev) interactively"
        )
        if self.confirm(question, True):
            dev_requirements = self._format_requirements(
                self._determine_requirements(self.option("dev-dependency"))
            )

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
        if self.input.is_interactive():
            self.line("<info>Generated file</info>")
            self.line(["", content, ""])

        if not self.confirm("Do you confirm generation?", True):
            self.line("<error>Command aborted</error>")

            return 1

        with (Path.cwd() / "pyproject.toml").open("w") as f:
            f.write(content)

    def _determine_requirements(
        self, requires, allow_prereleases=False  # type: List[str]  # type: bool
    ):  # type: (...) -> List[str]
        if not requires:
            requires = []

            package = self.ask("Search for package:")
            while package is not None:
                matches = self._get_pool().search(package)

                if not matches:
                    self.line("<error>Unable to find package</error>")
                    package = False
                else:
                    choices = []

                    for found_package in matches:
                        choices.append(found_package.pretty_name)

                    self.line(
                        "Found <info>{}</info> packages matching <info>{}</info>".format(
                            len(matches), package
                        )
                    )

                    package = self.choice(
                        "\nEnter package # to add, or the complete package name if it is not listed",
                        choices,
                        attempts=3,
                    )

                # no constraint yet, determine the best version automatically
                if package is not False and " " not in package:
                    question = self.create_question(
                        "Enter the version constraint to require "
                        "(or leave blank to use the latest version):"
                    )
                    question.attempts = 3
                    question.validator = lambda x: (x or "").strip() or False

                    constraint = self.ask(question)

                    if constraint is False:
                        _, constraint = self._find_best_version_for_package(package)

                        self.line(
                            "Using version <info>{}</info> for <info>{}</info>".format(
                                constraint, package
                            )
                        )

                    package += " {}".format(constraint)

                if package is not False:
                    requires.append(package)

                package = self.ask("\nSearch for a package:")

            return requires

        requires = self._parse_name_version_pairs(requires)
        result = []
        for requirement in requires:
            if "version" not in requirement:
                # determine the best version automatically
                name, version = self._find_best_version_for_package(
                    requirement["name"], allow_prereleases=allow_prereleases
                )
                requirement["version"] = version
                requirement["name"] = name

                self.line(
                    "Using version <info>{}</> for <info>{}</>".format(version, name)
                )
            else:
                # check that the specified version/constraint exists
                # before we proceed
                name, _ = self._find_best_version_for_package(
                    requirement["name"],
                    requirement["version"],
                    allow_prereleases=allow_prereleases,
                )

                requirement["name"] = name

            result.append("{} {}".format(requirement["name"], requirement["version"]))

        return result

    def _find_best_version_for_package(
        self, name, required_version=None, allow_prereleases=False
    ):  # type: (...) -> Tuple[str, str]
        from poetry.version.version_selector import VersionSelector

        selector = VersionSelector(self._get_pool())
        package = selector.find_best_candidate(
            name, required_version, allow_prereleases=allow_prereleases
        )

        if not package:
            # TODO: find similar
            raise ValueError(
                "Could not find a matching version of package {}".format(name)
            )

        return (package.pretty_name, selector.find_recommended_require_version(package))

    def _parse_name_version_pairs(self, pairs):  # type: (list) -> list
        result = []

        for i in range(len(pairs)):
            pair = re.sub("^([^=: ]+)[=: ](.*)$", "\\1 \\2", pairs[i].strip())
            pair = pair.strip()

            if " " in pair:
                name, version = pair.split(" ", 2)
                result.append({"name": name, "version": version})
            else:
                result.append({"name": pair})

        return result

    def _format_requirements(self, requirements):  # type: (List[str]) -> dict
        requires = {}
        requirements = self._parse_name_version_pairs(requirements)
        for requirement in requirements:
            requires[requirement["name"]] = requirement["version"]

        return requires

    def _validate_author(self, author, default):
        from poetry.packages.package import AUTHOR_REGEX

        author = author or default

        if author in ["n", "no"]:
            return

        m = AUTHOR_REGEX.match(author)
        if not m:
            raise ValueError(
                "Invalid author string. Must be in the format: "
                "John Smith <john@example.com>"
            )

        return author

    def _validate_license(self, license):
        from poetry.spdx import license_by_id

        if license:
            license_by_id(license)

        return license

    def _get_pool(self):
        from poetry.repositories import Pool
        from poetry.repositories.pypi_repository import PyPiRepository

        if isinstance(self, EnvCommand):
            return self.poetry.pool

        if self._pool is None:
            self._pool = Pool()
            self._pool.add_repository(PyPiRepository())

        return self._pool
