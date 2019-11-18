import os
import re

from typing import Generator
from typing import Optional

from cleo import argument
from cleo import option

from poetry.utils._compat import Path

from .command import Command


class VersionCommand(Command):

    name = "version"
    description = (
        "Shows the version of the project or bumps it when a valid"
        "bump rule is provided."
    )

    arguments = [
        argument(
            "version",
            "The version number or the rule to update the version.",
            optional=True,
        )
    ]

    options = [
        option(
            "sync",
            description=(
                "Synchronize version from pyproject.toml with __version__. "
                "If no value is passed to this option then file with __version__ "
                "will be guessed based on package name. If value is specified then it "
                "will be treated as path to the file with __version__."
            ),
            flag=False,
            value_required=False,
        ),
    ]

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

    def handle(self):
        version = self.argument("version")
        sync = self.option("sync")

        if version:
            version = self.increment_version(
                self.poetry.package.pretty_version, version
            )

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
            self.line(
                "Project (<comment>{}</>) version is <info>{}</>".format(
                    self.poetry.package.name, self.poetry.package.pretty_version
                )
            )
            version = self.poetry.package.version

        if sync is not None:
            self.sync_with_version_in_file(
                dir=None if sync in ("null", "-") else sync, version=version.text,
            )

    def increment_version(self, version, rule):
        from poetry.semver import Version

        try:
            version = Version.parse(version)
        except ValueError:
            raise ValueError("The project's version doesn't seem to follow semver")

        if rule in {"major", "premajor"}:
            new = version.next_major
            if rule == "premajor":
                new = new.first_prerelease
        elif rule in {"minor", "preminor"}:
            new = version.next_minor
            if rule == "preminor":
                new = new.first_prerelease
        elif rule in {"patch", "prepatch"}:
            new = version.next_patch
            if rule == "prepatch":
                new = new.first_prerelease
        elif rule == "prerelease":
            if version.is_prerelease():
                pre = version.prerelease
                new_prerelease = int(pre[1]) + 1
                new = Version.parse(
                    "{}.{}.{}-{}".format(
                        version.major,
                        version.minor,
                        version.patch,
                        ".".join([pre[0], str(new_prerelease)]),
                    )
                )
            else:
                new = version.next_patch.first_prerelease
        else:
            new = Version.parse(rule)

        return new

    def sync_with_version_in_file(
        self, dir, version
    ):  # type: (Optional[str], str) -> None
        finder = VersionFinder(self.poetry.package.name, self.poetry.file.parent)
        if dir:
            version_file = finder.find_file_in_dir(dir)
        else:
            version_file = finder.find_file()

        if not version_file:
            if dir:
                self.line("<warning>__version__ wasn't found in {}.</>".format(dir))
            else:
                self.line("<warning>__version__ wasn't found.</>")
            return

        with version_file.open("r") as file:
            file_content = file.read()

        old_version = finder.version_var_re.match(file_content).group(2)
        if old_version == version:
            self.line("<info>Versions are already in sync.</>")
            return

        new_file_content = finder.version_var_re.sub(
            r"\g<1>{}\g<3>".format(version), file_content, count=1,
        )
        version_file.write_text(new_file_content)
        self.line(
            "Changing <b>__version__</> (<info>{}</>) to <fg=green>{}</>".format(
                version_file, version
            )
        )


class VersionFinder(object):
    def __init__(self, package_name, package_root):  # type: (str, Path) -> None
        self.package_name = package_name.replace("-", "_")
        self.package_root = package_root
        self.version_var_re = re.compile(
            r"""
            ([\s\S]*  # left part of file
            ^\s*  # start of line with possible indent
            __version__  # variable name
            .*=\s*  # other variables and assign sign
            [urf]?[\"'])(.+)([\"']  # string literal with version
            [\s\S]*)  # right part of file
            """,
            flags=re.VERBOSE | re.MULTILINE,
        )

    def _iter_files(self):  # type: () -> Generator[Path, None, None]
        file_path = self.package_root.joinpath("{}.py".format(self.package_name))
        if file_path.exists():
            yield file_path
        for fp in self._iter_files_in_dir(self.package_name):
            yield fp

    def _iter_files_in_dir(
        self, dir_path
    ):  # type: (str) -> Generator[Path, None, None]
        module_files_pattern = "{}/*.py".format(dir_path)
        for file_path in self.package_root.glob(module_files_pattern):
            if file_path.name.startswith("__"):
                yield file_path

    def has_version_variable(self, file_path):  # type: (Path) -> bool
        with file_path.open() as file:
            file_headed = file.read(1024)
        match = self.version_var_re.match(file_headed)
        return bool(match)

    def find_file_in_dir(self, dir_path):  # type: (str) -> Optional[Path]
        if os.path.isfile(dir_path):
            file_path = Path(dir_path)
            if self.has_version_variable(file_path):
                return file_path
            return
        for file_path in self._iter_files_in_dir(dir_path):
            if self.has_version_variable(file_path):
                return file_path

    def find_file(self):  # type: () -> Optional[Path]
        for file_path in self._iter_files():
            if self.has_version_variable(file_path):
                return file_path
