# -*- coding: utf-8 -*-
import os
import re
import shutil
import tempfile

from collections import defaultdict
from contextlib import contextmanager
from typing import Set
from typing import Union

from poetry.utils._compat import Path
from poetry.utils._compat import basestring
from poetry.utils._compat import glob
from poetry.utils._compat import lru_cache
from poetry.utils._compat import to_str
from poetry.vcs import get_vcs

from ..metadata import Metadata
from ..utils.module import Module
from ..utils.package_include import PackageInclude


AUTHOR_REGEX = re.compile(r"(?u)^(?P<name>[- .,\w\d'’\"()]+) <(?P<email>.+?)>$")

METADATA_BASE = """\
Metadata-Version: 2.1
Name: {name}
Version: {version}
Summary: {summary}
"""


class Builder(object):

    AVAILABLE_PYTHONS = {"2", "2.7", "3", "3.4", "3.5", "3.6", "3.7"}

    def __init__(self, poetry, env, io):  # type: (Poetry, Env, IO) -> None
        self._poetry = poetry
        self._env = env
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

    @lru_cache(maxsize=None)
    def find_excluded_files(self):  # type: () -> Set[str]
        # Checking VCS
        vcs = get_vcs(self._path)
        if not vcs:
            vcs_ignored_files = set()
        else:
            vcs_ignored_files = set(vcs.get_ignored_files())

        explicitely_excluded = set()
        for excluded_glob in self._package.exclude:
            for excluded in glob(
                os.path.join(self._path.as_posix(), str(excluded_glob)), recursive=True
            ):
                explicitely_excluded.add(
                    Path(excluded).relative_to(self._path).as_posix()
                )

        ignored = vcs_ignored_files | explicitely_excluded
        result = set()
        for file in ignored:
            result.add(file)

        # The list of excluded files might be big and we will do a lot
        # containment check (x in excluded).
        # Returning a set make those tests much much faster.
        return result

    def is_excluded(self, filepath):  # type: (Union[str, Path]) -> bool
        if not isinstance(filepath, basestring):
            filepath = filepath.as_posix()

        return filepath in self.find_excluded_files()

    def find_files_to_add(self, exclude_build=True):  # type: (bool) -> list
        """
        Finds all files to add to the tarball
        """
        to_add = []

        for include in self._module.includes:
            for file in include.elements:
                if "__pycache__" in str(file):
                    continue

                if file.is_dir():
                    continue

                file = file.relative_to(self._path)

                if self.is_excluded(file) and isinstance(include, PackageInclude):
                    continue

                if file.suffix == ".pyc":
                    continue

                if file in to_add:
                    # Skip duplicates
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

    def get_metadata_content(self):  # type: () -> bytes
        content = METADATA_BASE.format(
            name=self._meta.name,
            version=self._meta.version,
            summary=to_str(self._meta.summary),
        )

        # Optional fields
        if self._meta.home_page:
            content += "Home-page: {}\n".format(self._meta.home_page)

        if self._meta.license:
            content += "License: {}\n".format(self._meta.license)

        if self._meta.keywords:
            content += "Keywords: {}\n".format(self._meta.keywords)

        if self._meta.author:
            content += "Author: {}\n".format(to_str(self._meta.author))

        if self._meta.author_email:
            content += "Author-email: {}\n".format(to_str(self._meta.author_email))

        if self._meta.requires_python:
            content += "Requires-Python: {}\n".format(self._meta.requires_python)

        for classifier in self._meta.classifiers:
            content += "Classifier: {}\n".format(classifier)

        for extra in sorted(self._meta.provides_extra):
            content += "Provides-Extra: {}\n".format(extra)

        for dep in sorted(self._meta.requires_dist):
            content += "Requires-Dist: {}\n".format(dep)

        for url in sorted(self._meta.project_urls, key=lambda u: u[0]):
            content += "Project-URL: {}\n".format(to_str(url))

        if self._meta.description_content_type:
            content += "Description-Content-Type: {}\n".format(
                self._meta.description_content_type
            )

        if self._meta.description is not None:
            content += "\n" + to_str(self._meta.description) + "\n"

        return content

    def convert_entry_points(self):  # type: () -> dict
        result = defaultdict(list)

        # Scripts -> Entry points
        for name, ep in self._poetry.local_config.get("scripts", {}).items():
            extras = ""
            if isinstance(ep, dict):
                extras = "[{}]".format(", ".join(ep["extras"]))
                ep = ep["callable"]

            result["console_scripts"].append("{} = {}{}".format(name, ep, extras))

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
