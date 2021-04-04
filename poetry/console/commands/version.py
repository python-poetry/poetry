from typing import TYPE_CHECKING

from cleo.helpers import argument
from cleo.helpers import option

from .command import Command


if TYPE_CHECKING:
    from poetry.core.semver.version import Version


class VersionCommand(Command):

    name = "version"
    description = (
        "Shows the version of the project or bumps it when a valid "
        "bump rule is provided."
    )

    arguments = [
        argument(
            "version",
            "The version number or the rule to update the version.",
            optional=True,
        )
    ]
    options = [option("short", "s", "Output the version number only")]

    help = """\
The version command shows the current version of the project or bumps the version of
the project and writes the new version back to <comment>pyproject.toml</> if a valid
bump rule is provided.

The new version should ideally be a valid semver string or a valid bump rule:
patch, minor, major, prepatch, preminor, premajor, prerelease.
"""

    RESERVED = {
        "major",
        "minor",
        "patch",
        "premajor",
        "preminor",
        "prepatch",
        "prerelease",
    }

    def handle(self) -> None:
        version = self.argument("version")

        if version:
            version = self.increment_version(
                self.poetry.package.pretty_version, version
            )

            if self.option("short"):
                self.line("{}".format(version))
            else:
                self.line(
                    "Bumping version from <b>{}</> to <fg=green>{}</>".format(
                        self.poetry.package.pretty_version, version
                    )
                )

            content = self.poetry.file.read()
            poetry_content = content["tool"]["poetry"]
            poetry_content["version"] = version.text

            self.poetry.file.write(content)
        else:
            if self.option("short"):
                self.line("{}".format(self.poetry.package.pretty_version))
            else:
                self.line(
                    "<comment>{}</> <info>{}</>".format(
                        self.poetry.package.name, self.poetry.package.pretty_version
                    )
                )

    def increment_version(self, version: str, rule: str) -> "Version":
        from poetry.core.semver.version import Version

        try:
            version = Version.parse(version)
        except ValueError:
            raise ValueError("The project's version doesn't seem to follow semver")

        if rule in {"major", "premajor"}:
            new = version.next_major()
            if rule == "premajor":
                new = new.first_prerelease()
        elif rule in {"minor", "preminor"}:
            new = version.next_minor()
            if rule == "preminor":
                new = new.first_prerelease()
        elif rule in {"patch", "prepatch"}:
            new = version.next_patch()
            if rule == "prepatch":
                new = new.first_prerelease()
        elif rule == "prerelease":
            if version.is_unstable():
                new = Version(version.epoch, version.release, version.pre.next())
            else:
                new = version.next_patch().first_prerelease()
        else:
            new = Version.parse(rule)

        return new
