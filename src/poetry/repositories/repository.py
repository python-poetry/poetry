from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from poetry.core.semver.helpers import parse_constraint
from poetry.core.semver.version_constraint import VersionConstraint
from poetry.core.semver.version_range import VersionRange


if TYPE_CHECKING:
    from poetry.core.packages.dependency import Dependency
    from poetry.core.packages.package import Package
    from poetry.core.packages.utils.link import Link
    from poetry.core.semver.helpers import VersionTypes


class Repository:
    def __init__(self, name: str = None, packages: list[Package] = None) -> None:
        self._name = name
        self._packages: list[Package] = []

        for package in packages or []:
            self.add_package(package)

    @property
    def name(self) -> str | None:
        return self._name

    @property
    def packages(self) -> list[Package]:
        return self._packages

    def find_packages(self, dependency: Dependency) -> list[Package]:
        packages = []
        ignored_pre_release_packages = []
        constraint, allow_prereleases = self._get_constraints_from_dependency(
            dependency
        )

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
                    and constraint.allows(package.version.next_patch())
                ):
                    packages.append(package)

        return packages or ignored_pre_release_packages

    def has_package(self, package: Package) -> bool:
        package_id = package.unique_name
        return any(
            package_id == repo_package.unique_name for repo_package in self.packages
        )

    def add_package(self, package: Package) -> None:
        self._packages.append(package)

    def remove_package(self, package: Package) -> None:
        package_id = package.unique_name

        index = None
        for i, repo_package in enumerate(self.packages):
            if package_id == repo_package.unique_name:
                index = i
                break

        if index is not None:
            del self._packages[index]

    def search(self, query: str) -> list[Package]:
        results: list[Package] = []

        for package in self.packages:
            if query in package.name:
                results.append(package)

        return results

    @staticmethod
    def _get_constraints_from_dependency(
        dependency: Dependency,
    ) -> tuple[VersionTypes, bool]:
        constraint = dependency.constraint
        if constraint is None:
            constraint = "*"

        if not isinstance(constraint, VersionConstraint):
            constraint = parse_constraint(constraint)

        allow_prereleases = dependency.allows_prereleases()
        if isinstance(constraint, VersionRange) and (
            constraint.max is not None
            and constraint.max.is_unstable()
            or constraint.min is not None
            and constraint.min.is_unstable()
        ):
            allow_prereleases = True

        return constraint, allow_prereleases

    def _log(self, msg: str, level: str = "info") -> None:
        getattr(logging.getLogger(self.__class__.__name__), level)(
            f"<debug>{self.name}:</debug> {msg}"
        )

    def __len__(self) -> int:
        return len(self._packages)

    def find_links_for_package(self, package: Package) -> list[Link]:
        return []

    def package(
        self, name: str, version: str, extras: list[str] | None = None
    ) -> Package:
        name = name.lower()

        for package in self.packages:
            if name == package.name and package.version.text == version:
                return package.clone()
