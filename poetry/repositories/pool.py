from typing import Dict
from typing import List
from typing import Optional

from .base_repository import BaseRepository
from .exceptions import PackageNotFound
from .repository import Repository


class Pool(BaseRepository):
    def __init__(
        self, repositories=None, ignore_repository_names=False
    ):  # type: (Optional[List[Repository]], bool) -> None
        if repositories is None:
            repositories = []

        self._lookup = {}  # type: Dict[str, int]
        self._repositories = []  # type: List[Repository]
        self._default = False
        self._secondary_start_idx = None

        for repository in repositories:
            self.add_repository(repository)

        self._ignore_repository_names = ignore_repository_names

        super(Pool, self).__init__()

    @property
    def repositories(self):  # type: () -> List[Repository]
        return self._repositories

    def has_default(self):  # type: () -> bool
        return self._default

    def repository(self, name):  # type: (str) -> Repository
        if name in self._lookup:
            return self._repositories[self._lookup[name]]

        raise ValueError('Repository "{}" does not exist.'.format(name))

    def add_repository(
        self, repository, default=False, secondary=False
    ):  # type: (Repository, bool, bool) -> Pool
        """
        Adds a repository to the pool.
        """
        if default:
            if self.has_default():
                raise ValueError("Only one repository can be the default")

            self._default = True
            self._repositories.insert(0, repository)
            for name in self._lookup:
                self._lookup[name] += 1

            if self._secondary_start_idx is not None:
                self._secondary_start_idx += 1

            self._lookup[repository.name] = 0
        elif secondary:
            if self._secondary_start_idx is None:
                self._secondary_start_idx = len(self._repositories)

            self._repositories.append(repository)
            self._lookup[repository.name] = len(self._repositories) - 1
        else:
            if self._secondary_start_idx is None:
                self._repositories.append(repository)
                self._lookup[repository.name] = len(self._repositories) - 1
            else:
                self._repositories.insert(self._secondary_start_idx, repository)

                for name, idx in self._lookup.items():
                    if idx < self._secondary_start_idx:
                        continue

                    self._lookup[name] += 1

                self._lookup[repository.name] = self._secondary_start_idx
                self._secondary_start_idx += 1

        return self

    def remove_repository(self, repository_name):  # type: (str) -> Pool
        idx = self._lookup.get(repository_name)
        if idx is not None:
            del self._repositories[idx]

        return self

    def has_package(self, package):
        raise NotImplementedError()

    def package(
        self, name, version, extras=None, repository=None
    ):  # type: (str, str, List[str], str) -> "Package"
        if (
            repository is not None
            and repository not in self._lookup
            and not self._ignore_repository_names
        ):
            raise ValueError('Repository "{}" does not exist.'.format(repository))

        if repository is not None and not self._ignore_repository_names:
            try:
                return self._repositories[self._lookup[repository]].package(
                    name, version, extras=extras
                )
            except PackageNotFound:
                pass
        else:
            for idx, repo in enumerate(self._repositories):
                try:
                    package = repo.package(name, version, extras=extras)
                except PackageNotFound:
                    continue

                if package:
                    self._packages.append(package)

                    return package

        raise PackageNotFound("Package {} ({}) not found.".format(name, version))

    def find_packages(
        self,
        name,
        constraint=None,
        extras=None,
        allow_prereleases=False,
        repository=None,
    ):
        if (
            repository is not None
            and repository not in self._lookup
            and not self._ignore_repository_names
        ):
            raise ValueError('Repository "{}" does not exist.'.format(repository))

        if repository is not None and not self._ignore_repository_names:
            return self._repositories[self._lookup[repository]].find_packages(
                name, constraint, extras=extras, allow_prereleases=allow_prereleases
            )

        packages = []
        for idx, repo in enumerate(self._repositories):
            packages += repo.find_packages(
                name, constraint, extras=extras, allow_prereleases=allow_prereleases
            )

        return packages

    def search(self, query):
        from .legacy_repository import LegacyRepository

        results = []
        for repository in self._repositories:
            if isinstance(repository, LegacyRepository):
                continue

            results += repository.search(query)

        return results
