from poetry.semver import parse_constraint
from poetry.semver import VersionConstraint

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

        for package in self.packages:
            if name == package.name and package.version.text == version:
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

        if not isinstance(constraint, VersionConstraint):
            constraint = parse_constraint(constraint)

        for package in self.packages:
            if name == package.name:
                if package.is_prerelease() and not allow_prereleases:
                    continue

                if constraint is None or constraint.allows(package.version):
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
