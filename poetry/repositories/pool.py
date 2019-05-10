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
        self._default = None

        for repository in repositories:
            self.add_repository(repository)

        self._ignore_repository_names = ignore_repository_names

        super(Pool, self).__init__()

    @property
    def repositories(self):  # type: () -> List[Repository]
        return self._repositories

    @property
    def default(self):  # type: () -> Optional[Repository]
        if self._default is None:
            return

        return self._repositories[self._default]

    def has_default(self):  # type: () -> bool
        return self._default is not None

    def add_repository(
        self, repository, default=False
    ):  # type: (Repository, bool) -> Pool
        """
        Adds a repository to the pool.
        """
        if default:
            if self.has_default():
                raise ValueError("Only one repository can be the default")

            self._repositories.append(repository)
            self._default = len(self._repositories) - 1
            self._lookup[repository.name] = self._default
        else:
            if self.has_default():
                default_repository = self.default
                self._repositories.insert(self._default, repository)
                self._lookup[repository.name] = self._default

                self._default = len(self._repositories) - 1
                self._lookup[default_repository.name] = self._default
            else:
                self._repositories.append(repository)
                self._lookup[repository.name] = len(self._repositories) - 1

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
    ):  # type: (str, str, List[str], str) -> Package
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
            for repo in self._repositories:
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
        for repo in self._repositories:
            packages += repo.find_packages(
                name, constraint, extras=extras, allow_prereleases=allow_prereleases
            )

        return packages

    def search(self, query, mode=BaseRepository.SEARCH_FULLTEXT):
        from .legacy_repository import LegacyRepository

        results = []
        for repository in self._repositories:
            if isinstance(repository, LegacyRepository):
                continue

            results += repository.search(query, mode=mode)

        return results
