from poetry.core.semver import VersionConstraint
from poetry.core.semver import VersionRange
from poetry.core.semver import parse_constraint

from .base_repository import BaseRepository


class Repository(BaseRepository):
    def __init__(self, packages=None, name=None):
        super(Repository, self).__init__()

        self._name = name

        if packages is None:
            packages = []

        for package in packages:
            self.add_package(package)

    @property
    def name(self):
        return self._name

    def package(self, name, version, extras=None):
        name = name.lower()

        for package in self.packages:
            if name == package.name and package.version.text == version:
                return package.clone()

    def find_packages(self, dependency):
        constraint = dependency.constraint
        packages = []
        ignored_pre_release_packages = []

        if constraint is None:
            constraint = "*"

        if not isinstance(constraint, VersionConstraint):
            constraint = parse_constraint(constraint)

        allow_prereleases = dependency.allows_prereleases()
        if isinstance(constraint, VersionRange):
            if (
                constraint.max is not None
                and constraint.max.is_prerelease()
                or constraint.min is not None
                and constraint.min.is_prerelease()
            ):
                allow_prereleases = True

        for package in self.packages:
            if dependency.name == package.name:
                if (
                    package.is_prerelease()
                    and not allow_prereleases
                    and not package.source_type
                ):
                    # If prereleases are not allowed and the package is a prerelease
                    # and is a standard package then we skip it
                    if constraint.is_any():
                        # we need this when all versions of the package are pre-releases
                        ignored_pre_release_packages.append(package)
                    continue

                if constraint.allows(package.version) or (
                    package.is_prerelease()
                    and constraint.allows(package.version.next_patch)
                ):
                    packages.append(package)

        return packages or ignored_pre_release_packages

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

    def find_links_for_package(self, package):
        return []

    def search(self, query):
        results = []

        for package in self.packages:
            if query in package.name:
                results.append(package)

        return results

    def __len__(self):
        return len(self._packages)
