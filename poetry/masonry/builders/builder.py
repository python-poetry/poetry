# -*- coding: utf-8 -*-
import os
import re
import shutil
import tempfile

from collections import defaultdict
from contextlib import contextmanager

from poetry.utils._compat import Path
from poetry.vcs import get_vcs

from ..metadata import Metadata
from ..utils.module import Module
from ..utils.package_include import PackageInclude


AUTHOR_REGEX = re.compile("(?u)^(?P<name>[- .,\w\d'’\"()]+) <(?P<email>.+?)>$")


class Builder(object):

    AVAILABLE_PYTHONS = {"2", "2.7", "3", "3.4", "3.5", "3.6", "3.7"}

    def __init__(self, poetry, venv, io):
        self._poetry = poetry
        self._venv = venv
        self._io = io
        self._package = poetry.package
        self._path = poetry.file.parent
        self._module = Module(
            self._package.name,
            self._path.as_posix(),
            packages=self._package.packages,
            includes=self._package.include,
        )
        self._meta = Metadata.from_package(self._package)

    def build(self):
        raise NotImplementedError()

    def find_excluded_files(self):  # type: () -> list
        # Checking VCS
        vcs = get_vcs(self._path)
        if not vcs:
            return []

        explicitely_excluded = []
        for excluded_glob in self._package.exclude:
            for excluded in self._path.glob(excluded_glob):
                explicitely_excluded.append(excluded)

        ignored = vcs.get_ignored_files() + explicitely_excluded
        result = []
        for file in ignored:
            try:
                file = Path(file).absolute().relative_to(self._path)
            except ValueError:
                # Should only happen in tests
                continue

            result.append(file)

        return result

    def find_files_to_add(self, exclude_build=True):  # type: () -> list
        """
        Finds all files to add to the tarball
        """
        excluded = self.find_excluded_files()
        src = self._module.path
        to_add = []

        for include in self._module.includes:
            for file in include.elements:
                if "__pycache__" in str(file):
                    continue

                if file.is_dir():
                    continue

                file = file.relative_to(self._path)

                if file in excluded and isinstance(include, PackageInclude):
                    continue

                if file.suffix == ".pyc":
                    continue

                self._io.writeln(
                    " - Adding: <comment>{}</comment>".format(str(file)),
                    verbosity=self._io.VERBOSITY_VERY_VERBOSE,
                )
                to_add.append(file)

        # Include project files
        self._io.writeln(
            " - Adding: <comment>pyproject.toml</comment>",
            verbosity=self._io.VERBOSITY_VERY_VERBOSE,
        )
        to_add.append(Path("pyproject.toml"))

        # If a license file exists, add it
        for license_file in self._path.glob("LICENSE*"):
            self._io.writeln(
                " - Adding: <comment>{}</comment>".format(
                    license_file.relative_to(self._path)
                ),
                verbosity=self._io.VERBOSITY_VERY_VERBOSE,
            )
            to_add.append(license_file.relative_to(self._path))

        # If a README is specificed we need to include it
        # to avoid errors
        if "readme" in self._poetry.local_config:
            readme = self._path / self._poetry.local_config["readme"]
            if readme.exists():
                self._io.writeln(
                    " - Adding: <comment>{}</comment>".format(
                        readme.relative_to(self._path)
                    ),
                    verbosity=self._io.VERBOSITY_VERY_VERBOSE,
                )
                to_add.append(readme.relative_to(self._path))

        # If a build script is specified and explicitely required
        # we add it to the list of files
        if self._package.build and not exclude_build:
            to_add.append(Path(self._package.build))

        return sorted(to_add)

    def convert_entry_points(self):  # type: () -> dict
        result = defaultdict(list)

        # Scripts -> Entry points
        for name, ep in self._poetry.local_config.get("scripts", {}).items():
            result["console_scripts"].append("{} = {}".format(name, ep))

        # Plugins -> entry points
        plugins = self._poetry.local_config.get("plugins", {})
        for groupname, group in plugins.items():
            for name, ep in sorted(group.items()):
                result[groupname].append("{} = {}".format(name, ep))

        for groupname in result:
            result[groupname] = sorted(result[groupname])

        return dict(result)

    @classmethod
    def convert_author(cls, author):  # type: () -> dict
        m = AUTHOR_REGEX.match(author)

        name = m.group("name")
        email = m.group("email")

        return {"name": name, "email": email}

    @classmethod
    @contextmanager
    def temporary_directory(cls, *args, **kwargs):
        try:
            from tempfile import TemporaryDirectory

            with TemporaryDirectory(*args, **kwargs) as name:
                yield name
        except ImportError:
            name = tempfile.mkdtemp(*args, **kwargs)

            yield name

            shutil.rmtree(name)
