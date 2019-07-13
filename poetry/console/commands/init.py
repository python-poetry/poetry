# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import re

from typing import Dict
from typing import List
from typing import Tuple
from typing import Union

from cleo import option
from tomlkit import inline_table

from poetry.utils._compat import Path
from poetry.utils._compat import OrderedDict

from .command import Command
from .env_command import EnvCommand


class InitCommand(Command):

    name = "init"
    description = (
        "Creates a basic <comment>pyproject.toml</> file in the current directory."
    )

    options = [
        option("name", None, "Name of the package.", flag=False),
        option("description", None, "Description of the package.", flag=False),
        option("author", None, "Author name of the package.", flag=False),
        option(
            "dependency",
            None,
            "Package to require with an optional version constraint, "
            "e.g. requests:^2.10.0 or requests=2.11.1.",
            flag=False,
            multiple=True,
        ),
        option(
            "dev-dependency",
            None,
            "Package to require for development with an optional version constraint, "
            "e.g. requests:^2.10.0 or requests=2.11.1.",
            flag=False,
            multiple=True,
        ),
        option("license", "l", "License of the package.", flag=False),
    ]

    help = """\
The <info>init</info> command creates a basic <comment>pyproject.toml</> file in the current directory.
"""

    def __init__(self):
        super(InitCommand, self).__init__()

        self._pool = None

    def handle(self):
        from poetry.layouts import layout
        from poetry.utils._compat import Path
        from poetry.utils.env import EnvManager
        from poetry.vcs.git import GitConfig

        if (Path.cwd() / "pyproject.toml").exists():
            self.line("<error>A pyproject.toml file already exists.</error>")
            return 1

        vcs_config = GitConfig()

        self.line("")
        self.line(
            "This command will guide you through creating your <info>pyproject.toml</> config."
        )
        self.line("")

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
        question.set_validator(lambda v: self._validate_author(v, author))
        author = self.ask(question)

        if not author:
            authors = []
        else:
            authors = [author]

        license = self.option("license") or ""

        question = self.create_question(
            "License [<comment>{}</comment>]: ".format(license), default=license
        )
        question.set_validator(self._validate_license)
        license = self.ask(question)

        current_env = EnvManager().get(Path.cwd())
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

        question = "Would you like to define your main dependencies interactively?"
        help_message = (
            "You can specify a package in the following forms:\n"
            "  - A single name (<b>requests</b>)\n"
            "  - A name and a constraint (<b>requests ^2.23.0</b>)\n"
            "  - A git url (<b>https://github.com/sdispater/poetry.git</b>)\n"
            "  - A git url with a revision (<b>https://github.com/sdispater/poetry.git@develop</b>)\n"
            "  - A file path (<b>../my-package/my-package.whl</b>)\n"
            "  - A directory (<b>../my-package/</b>)\n"
        )
        help_displayed = False
        if self.confirm(question, True):
            self.line(help_message)
            help_displayed = True
            requirements = self._format_requirements(
                self._determine_requirements(self.option("dependency"))
            )
            self.line("")

        dev_requirements = {}

        question = (
            "Would you like to define your dev dependencies"
            " (require-dev) interactively"
        )
        if self.confirm(question, True):
            if not help_displayed:
                self.line(help_message)

            dev_requirements = self._format_requirements(
                self._determine_requirements(self.option("dev-dependency"))
            )
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
        if self.io.is_interactive():
            self.line("<info>Generated file</info>")
            self.line("")
            self.line(content)
            self.line("")

        if not self.confirm("Do you confirm generation?", True):
            self.line("<error>Command aborted</error>")

            return 1

        with (Path.cwd() / "pyproject.toml").open("w", encoding="utf-8") as f:
            f.write(content)

    def _determine_requirements(
        self, requires, allow_prereleases=False
    ):  # type: (List[str], bool) -> List[Dict[str, str]]
        if not requires:
            requires = []

            package = self.ask("Add a package:")
            while package is not None:
                constraint = self._parse_requirements([package])[0]
                if (
                    "git" in constraint
                    or "path" in constraint
                    or "version" in constraint
                ):
                    self.line("Adding <info>{}</info>".format(package))
                    requires.append(constraint)
                    package = self.ask("\nAdd a package:")
                    continue

                matches = self._get_pool().search(constraint["name"])

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
                if package is not False and "version" not in constraint:
                    question = self.create_question(
                        "Enter the version constraint to require "
                        "(or leave blank to use the latest version):"
                    )
                    question.attempts = 3
                    question.validator = lambda x: (x or "").strip() or False

                    package_constraint = self.ask(question)

                    if package_constraint is None:
                        _, package_constraint = self._find_best_version_for_package(
                            package
                        )

                        self.line(
                            "Using version <info>{}</info> for <info>{}</info>".format(
                                package_constraint, package
                            )
                        )

                    constraint["version"] = package_constraint

                if package is not False:
                    requires.append(constraint)

                package = self.ask("\nAdd a package:")

            return requires

        requires = self._parse_requirements(requires)
        result = []
        for requirement in requires:
            if "git" in requirement or "path" in requirement:
                result.append(requirement)
                continue
            elif "version" not in requirement:
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

            result.append(requirement)

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

        return package.pretty_name, selector.find_recommended_require_version(package)

    def _parse_requirements(
        self, requirements
    ):  # type: (List[str]) -> List[Dict[str, str]]
        from poetry.puzzle.provider import Provider

        result = []

        try:
            cwd = self.poetry.file.parent
        except RuntimeError:
            cwd = Path.cwd()

        for requirement in requirements:
            requirement = requirement.strip()
            extras = []
            extras_m = re.search(r"\[([\w\d,-_]+)\]$", requirement)
            if extras_m:
                extras = [e.strip() for e in extras_m.group(1).split(",")]
                requirement, _ = requirement.split("[")

            if requirement.startswith(("git+https://", "git+ssh://")):
                url = requirement.lstrip("git+")
                rev = None
                if "@" in url:
                    url, rev = url.split("@")

                pair = OrderedDict(
                    [("name", url.split("/")[-1].rstrip(".git")), ("git", url)]
                )
                if rev:
                    pair["rev"] = rev

                if extras:
                    pair["extras"] = extras

                package = Provider.get_package_from_vcs(
                    "git", url, reference=pair.get("rev")
                )
                pair["name"] = package.name
                result.append(pair)

                continue
            elif (os.path.sep in requirement or "/" in requirement) and cwd.joinpath(
                requirement
            ).exists():
                path = cwd.joinpath(requirement)
                if path.is_file():
                    package = Provider.get_package_from_file(path.resolve())
                else:
                    package = Provider.get_package_from_directory(path)

                result.append(
                    OrderedDict(
                        [
                            ("name", package.name),
                            ("path", path.relative_to(cwd).as_posix()),
                        ]
                        + ([("extras", extras)] if extras else [])
                    )
                )

                continue

            pair = re.sub(
                "^([^@=: ]+)(?:@|==|(?<![<>~!])=|:| )(.*)$", "\\1 \\2", requirement
            )
            pair = pair.strip()

            require = OrderedDict()
            if " " in pair:
                name, version = pair.split(" ", 2)
                require["name"] = name
                require["version"] = version
            else:
                m = re.match(
                    "^([^><=!: ]+)((?:>=|<=|>|<|!=|~=|~|\^).*)$", requirement.strip()
                )
                if m:
                    name, constraint = m.group(1), m.group(2)
                    extras_m = re.search(r"\[([\w\d,-_]+)\]$", name)
                    if extras_m:
                        extras = [e.strip() for e in extras_m.group(1).split(",")]
                        name, _ = name.split("[")

                    require["name"] = name
                    require["version"] = constraint
                else:
                    extras_m = re.search(r"\[([\w\d,-_]+)\]$", pair)
                    if extras_m:
                        extras = [e.strip() for e in extras_m.group(1).split(",")]
                        pair, _ = pair.split("[")

                    require["name"] = pair

            if extras:
                require["extras"] = extras

            result.append(require)

        return result

    def _format_requirements(
        self, requirements
    ):  # type: (List[Dict[str, str]]) -> Dict[str, Union[str, Dict[str, str]]]
        requires = {}
        for requirement in requirements:
            name = requirement.pop("name")
            if "version" in requirement and len(requirement) == 1:
                constraint = requirement["version"]
            else:
                constraint = inline_table()
                constraint.trivia.trail = "\n"
                constraint.update(requirement)

            requires[name] = constraint

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
