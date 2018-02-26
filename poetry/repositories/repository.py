import re

from poetry.semver.constraints import Constraint
from poetry.semver.constraints.base_constraint import BaseConstraint
from poetry.semver.helpers import normalize_version
from poetry.semver.version_parser import VersionParser

from .base_repository import BaseRepository


class Repository(BaseRepository):

    def __init__(self, packages=None):
        super(Repository, self).__init__()

        if packages is None:
            packages = []

        for package in packages:
            self.add_package(package)

    def package(self, name, version):
        name = name.lower()
        version = normalize_version(version)

        for package in self.packages:
            if name == package.name and package.version == version:
                return package

    def find_packages(self, name, constraint=None):
        name = name.lower()
        packages = []

        if not isinstance(constraint, BaseConstraint):
            parser = VersionParser()
            constraint = parser.parse_constraints(constraint)

        for package in self.packages:
            if name == package.name:
                pkg_constraint = Constraint('==', package.version)

                if constraint is None or constraint.matches(pkg_constraint):
                    packages.append(package)

        return packages

    def search(self, query, mode=0):
        regex = '(?i)(?:{})'.format('|'.join(re.split('\s+', query)))

        matches = {}
        for package in self.packages:
            name = package.name

            if name in matches:
                continue

            if (
                re.match(regex, name) is not None
                or (
                    mode == self.SEARCH_FULLTEXT
                    and isinstance(package, CompletePackage)
                    and re.match(regex, '')
                )
            ):
                matches[name] = {
                    'name': package.pretty_name,
                    'description': (package.description
                                    if isinstance(package, CompletePackage)
                                    else '')
                }

        return list(matches.values())

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
