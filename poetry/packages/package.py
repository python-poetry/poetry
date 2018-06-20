# -*- coding: utf-8 -*-
import copy
import re

from contextlib import contextmanager
from typing import Union

from poetry.semver import Version
from poetry.semver import parse_constraint
from poetry.spdx import license_by_id
from poetry.spdx import License
from poetry.utils._compat import Path
from poetry.utils.helpers import canonicalize_name

from .constraints.empty_constraint import EmptyConstraint
from .constraints.generic_constraint import GenericConstraint
from .dependency import Dependency
from .directory_dependency import DirectoryDependency
from .file_dependency import FileDependency
from .vcs_dependency import VCSDependency

AUTHOR_REGEX = re.compile("(?u)^(?P<name>[- .,\w\d'’\"()]+)(?: <(?P<email>.+?)>)?$")


class Package(object):

    AVAILABLE_PYTHONS = {"2", "2.7", "3", "3.4", "3.5", "3.6", "3.7"}

    def __init__(self, name, version, pretty_version=None):
        """
        Creates a new in memory package.
        """
        self._pretty_name = name
        self._name = canonicalize_name(name)

        if not isinstance(version, Version):
            self._version = Version.parse(version)
            self._pretty_version = pretty_version or version
        else:
            self._version = version
            self._pretty_version = pretty_version or self._version.text

        self.description = ""

        self._authors = []

        self.homepage = None
        self.repository_url = None
        self.keywords = []
        self._license = None
        self.readme = None

        self.source_type = ""
        self.source_reference = ""
        self.source_url = ""

        self.requires = []
        self.dev_requires = []
        self.extras = {}
        self.requires_extras = []

        self.category = "main"
        self.hashes = []
        self.optional = False

        # Requirements for making it mandatory
        self.requirements = {}

        self.classifiers = []

        self._python_versions = "*"
        self._python_constraint = parse_constraint("*")
        self._platform = "*"
        self._platform_constraint = EmptyConstraint()

        self.root_dir = None

        self.develop = False

    @property
    def name(self):
        return self._name

    @property
    def pretty_name(self):
        return self._pretty_name

    @property
    def version(self):
        return self._version

    @property
    def pretty_version(self):
        return self._pretty_version

    @property
    def unique_name(self):
        if self.is_root():
            return self._name

        return self.name + "-" + self._version.text

    @property
    def pretty_string(self):
        return self.pretty_name + " " + self.pretty_version

    @property
    def full_pretty_version(self):
        if self.source_type not in ["hg", "git"]:
            return self._pretty_version

        # if source reference is a sha1 hash -- truncate
        if len(self.source_reference) == 40:
            return "{} {}".format(self._pretty_version, self.source_reference[0:7])

        return "{} {}".format(self._pretty_version, self.source_reference)

    @property
    def authors(self):  # type: () -> list
        return self._authors

    @property
    def author_name(self):  # type: () -> str
        return self._get_author()["name"]

    @property
    def author_email(self):  # type: () -> str
        return self._get_author()["email"]

    @property
    def all_requires(self):
        return self.requires + self.dev_requires

    def _get_author(self):  # type: () -> dict
        if not self._authors:
            return {"name": None, "email": None}

        m = AUTHOR_REGEX.match(self._authors[0])

        name = m.group("name")
        email = m.group("email")

        return {"name": name, "email": email}

    @property
    def python_versions(self):
        return self._python_versions

    @python_versions.setter
    def python_versions(self, value):
        self._python_versions = value
        self._python_constraint = parse_constraint(value)

    @property
    def python_constraint(self):
        return self._python_constraint

    @property
    def platform(self):  # type: () -> str
        return self._platform

    @platform.setter
    def platform(self, value):  # type: (str) -> None
        self._platform = value
        self._platform_constraint = GenericConstraint.parse(value)

    @property
    def platform_constraint(self):
        return self._platform_constraint

    @property
    def license(self):
        return self._license

    @license.setter
    def license(self, value):
        if value is None:
            self._license = value
        elif isinstance(value, License):
            self._license = value
        else:
            self._license = license_by_id(value)

    @property
    def all_classifiers(self):
        classifiers = copy.copy(self.classifiers)

        # Automatically set python classifiers
        if self.python_versions == "*":
            python_constraint = parse_constraint("~2.7 || ^3.4")
        else:
            python_constraint = self.python_constraint

        for version in sorted(self.AVAILABLE_PYTHONS):
            if len(version) == 1:
                constraint = parse_constraint(version + ".*")
            else:
                constraint = Version.parse(version)

            if python_constraint.allows_any(constraint):
                classifiers.append(
                    "Programming Language :: Python :: {}".format(version)
                )

        # Automatically set license classifiers
        if self.license:
            classifiers.append(self.license.classifier)

        classifiers = set(classifiers)

        return sorted(classifiers)

    def is_prerelease(self):
        return self._version.is_prerelease()

    def is_root(self):
        return False

    def add_dependency(
        self,
        name,  # type: str
        constraint=None,  # type: Union[str, dict, None]
        category="main",  # type: str
    ):  # type: (...) -> Dependency
        if constraint is None:
            constraint = "*"

        if isinstance(constraint, dict):
            optional = constraint.get("optional", False)
            python_versions = constraint.get("python")
            platform = constraint.get("platform")
            allows_prereleases = constraint.get("allows-prereleases", False)

            if "git" in constraint:
                # VCS dependency
                dependency = VCSDependency(
                    name,
                    "git",
                    constraint["git"],
                    branch=constraint.get("branch", None),
                    tag=constraint.get("tag", None),
                    rev=constraint.get("rev", None),
                    optional=optional,
                )
            elif "file" in constraint:
                file_path = Path(constraint["file"])

                dependency = FileDependency(
                    file_path, category=category, base=self.root_dir
                )
            elif "path" in constraint:
                path = Path(constraint["path"])

                if self.root_dir:
                    is_file = (self.root_dir / path).is_file()
                else:
                    is_file = path.is_file()

                if is_file:
                    dependency = FileDependency(
                        path, category=category, optional=optional, base=self.root_dir
                    )
                else:
                    dependency = DirectoryDependency(
                        path,
                        category=category,
                        optional=optional,
                        base=self.root_dir,
                        develop=constraint.get("develop", False),
                    )
            else:
                version = constraint["version"]

                dependency = Dependency(
                    name,
                    version,
                    optional=optional,
                    category=category,
                    allows_prereleases=allows_prereleases,
                )

            if python_versions:
                dependency.python_versions = python_versions

            if platform:
                dependency.platform = platform

            if "extras" in constraint:
                for extra in constraint["extras"]:
                    dependency.extras.append(extra)
        else:
            dependency = Dependency(name, constraint, category=category)

        if category == "dev":
            self.dev_requires.append(dependency)
        else:
            self.requires.append(dependency)

        return dependency

    def to_dependency(self):
        return Dependency(self.name, self._version)

    @contextmanager
    def with_python_versions(self, python_versions):
        original_python_versions = self.python_versions

        self.python_versions = python_versions

        yield

        self.python_versions = original_python_versions

    def clone(self):  # type: () -> Package
        clone = Package(self.pretty_name, self.version)
        clone.category = self.category
        clone.optional = self.optional
        clone.python_versions = self.python_versions
        clone.platform = self.platform
        clone.extras = self.extras
        clone.source_type = self.source_type
        clone.source_url = self.source_url
        clone.source_reference = self.source_reference

        for dep in self.requires:
            clone.requires.append(dep)

        return clone

    def __hash__(self):
        return hash((self._name, self._version))

    def __eq__(self, other):
        if not isinstance(other, Package):
            return NotImplemented

        return self._name == other.name and self._version == other.version

    def __str__(self):
        return self.unique_name

    def __repr__(self):
        return "<Package {}>".format(self.unique_name)
