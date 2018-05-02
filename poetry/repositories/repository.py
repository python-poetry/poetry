from poetry.semver.constraints import Constraint
from poetry.semver.constraints.base_constraint import BaseConstraint
from poetry.semver.version_parser import VersionParser

from poetry.version import parse as parse_version

from .base_repository import BaseRepository


class Repository(BaseRepository):

    def __init__(self, packages=None):
        super(Repository, self).__init__()

        if packages is None:
            packages = []

        for package in packages:
            self.add_package(package)

    def package(self, name, version, extras=None):
        name = name.lower()
        version = str(parse_version(version))

        for package in self.packages:
            if name == package.name and package.version == version:
                return package

    def find_packages(self, name, constraint=None,
                      extras=None,
                      allow_prereleases=False):
        name = name.lower()
        packages = []
        if extras is None:
            extras = []

        if constraint is None:
            constraint = '*'

        if not isinstance(constraint, BaseConstraint):
            parser = VersionParser()
            constraint = parser.parse_constraints(constraint)

        for package in self.packages:
            if name == package.name:
                pkg_constraint = Constraint('==', package.version)

                if constraint is None or constraint.matches(pkg_constraint):
                    for dep in package.requires:
                        for extra in extras:
                            if extra not in package.extras:
                                continue

                            reqs = package.extras[extra]
                            for req in reqs:
                                if req.name == dep.name:
                                    dep.activate()

                    packages.append(package)

        return packages

    def has_package(self, package):
        package_id = package.unique_name

        for repo_package in self.packages:
            if package_id == repo_package.unique_name:
                return True

        return False

    def add_package(self, package):
        self._packages.append(package)

    def remove_package(self, package):
        package_id = package.unique_name

        index = None
        for i, repo_package in enumerate(self.packages):
            if package_id == repo_package.unique_name:
                index = i
                break

        if index is not None:
            del self._packages[index]

    def __len__(self):
        return len(self._packages)
