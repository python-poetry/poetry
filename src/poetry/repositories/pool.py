from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.repositories.exceptions import PackageNotFound
from poetry.repositories.repository import Repository


if TYPE_CHECKING:
    from poetry.core.constraints.version import Version
    from poetry.core.packages.dependency import Dependency
    from poetry.core.packages.package import Package


class Pool(Repository):
    def __init__(
        self,
        repositories: list[Repository] | None = None,
        ignore_repository_names: bool = False,
    ) -> None:
        super().__init__("poetry-pool")

        if repositories is None:
            repositories = []

        self._lookup: dict[str, int] = {}
        self._repositories: list[Repository] = []
        self._default = False
        self._has_primary_repositories = False
        self._secondary_start_idx: int | None = None

        for repository in repositories:
            self.add_repository(repository)

        self._ignore_repository_names = ignore_repository_names

    @property
    def repositories(self) -> list[Repository]:
        return self._repositories

    def has_default(self) -> bool:
        return self._default

    def has_primary_repositories(self) -> bool:
        return self._has_primary_repositories

    def has_repository(self, name: str) -> bool:
        return name.lower() in self._lookup

    def repository(self, name: str) -> Repository:
        name = name.lower()

        lookup = self._lookup.get(name)
        if lookup is not None:
            return self._repositories[lookup]

        raise ValueError(f'Repository "{name}" does not exist.')

    def add_repository(
        self, repository: Repository, default: bool = False, secondary: bool = False
    ) -> Pool:
        """
        Adds a repository to the pool.
        """
        repository_name = repository.name.lower()
        if repository_name in self._lookup:
            raise ValueError(f"{repository_name} already added")

        if default:
            if self.has_default():
                raise ValueError("Only one repository can be the default")

            self._default = True
            self._repositories.insert(0, repository)
            for name in self._lookup:
                self._lookup[name] += 1

            if self._secondary_start_idx is not None:
                self._secondary_start_idx += 1

            self._lookup[repository_name] = 0
        elif secondary:
            if self._secondary_start_idx is None:
                self._secondary_start_idx = len(self._repositories)

            self._repositories.append(repository)
            self._lookup[repository_name] = len(self._repositories) - 1
        else:
            self._has_primary_repositories = True
            if self._secondary_start_idx is None:
                self._repositories.append(repository)
                self._lookup[repository_name] = len(self._repositories) - 1
            else:
                self._repositories.insert(self._secondary_start_idx, repository)

                for name, idx in self._lookup.items():
                    if idx < self._secondary_start_idx:
                        continue

                    self._lookup[name] += 1

                self._lookup[repository_name] = self._secondary_start_idx
                self._secondary_start_idx += 1

        return self

    def remove_repository(self, repository_name: str) -> Pool:
        if repository_name is not None:
            repository_name = repository_name.lower()

        idx = self._lookup.get(repository_name)
        if idx is not None:
            del self._repositories[idx]
            del self._lookup[repository_name]

            if idx == 0:
                self._default = False

            for name in self._lookup:
                if self._lookup[name] > idx:
                    self._lookup[name] -= 1

            if (
                self._secondary_start_idx is not None
                and self._secondary_start_idx > idx
            ):
                self._secondary_start_idx -= 1

        return self

    def has_package(self, package: Package) -> bool:
        raise NotImplementedError()

    def package(
        self,
        name: str,
        version: Version,
        extras: list[str] | None = None,
        repository: str | None = None,
    ) -> Package:
        if repository is not None:
            repository = repository.lower()

        if (
            repository is not None
            and repository not in self._lookup
            and not self._ignore_repository_names
        ):
            raise ValueError(f'Repository "{repository}" does not exist.')

        if repository is not None and not self._ignore_repository_names:
            return self.repository(repository).package(name, version, extras=extras)

        for repo in self._repositories:
            try:
                package = repo.package(name, version, extras=extras)
            except PackageNotFound:
                continue

            return package

        raise PackageNotFound(f"Package {name} ({version}) not found.")

    def find_packages(self, dependency: Dependency) -> list[Package]:
        repository = dependency.source_name
        if repository is not None:
            repository = repository.lower()

        if (
            repository is not None
            and repository not in self._lookup
            and not self._ignore_repository_names
        ):
            raise ValueError(f'Repository "{repository}" does not exist.')

        if repository is not None and not self._ignore_repository_names:
            return self.repository(repository).find_packages(dependency)

        packages = []
        for repo in self._repositories:
            packages += repo.find_packages(dependency)

        return packages

    def search(self, query: str) -> list[Package]:
        from poetry.repositories.legacy_repository import LegacyRepository

        results = []
        for repository in self._repositories:
            if isinstance(repository, LegacyRepository):
                continue

            results += repository.search(query)

        return results
