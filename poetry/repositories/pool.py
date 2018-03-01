from typing import List
from typing import Union

import poetry.packages

from .base_repository import BaseRepository
from .legacy_repository import LegacyRepository
from .repository import Repository


class Pool(BaseRepository):

    def __init__(self, repositories: Union[list, None] = None):
        if repositories is None:
            repositories = []

        self._repositories = []

        for repository in repositories:
            self.add_repository(repository)

        super().__init__()
            
    @property
    def repositories(self) -> List[Repository]:
        return self._repositories

    def add_repository(self, repository: Repository) -> 'Pool':
        """
        Adds a repository to the pool.
        """
        self._repositories.append(repository)

        return self
    
    def configure(self, source: dict) -> 'Pool':
        """
        Configures a repository based on a source
        specification and add it to the pool.
        """
        if 'url' in source:
            # PyPI-like repository
            if 'name' not in source:
                raise RuntimeError('Missing [name] in source.')

            repository = LegacyRepository(source['name'], source['url'])
        else:
            raise RuntimeError('Unsupported source specified')

        return self.add_repository(repository)

    def has_package(self, package):
        raise NotImplementedError()

    def package(self, name, version) -> Union['poetry.packages.Package', None]:
        package = poetry.packages.Package(name, version, version)
        if package in self._packages:
            return self._packages[self._packages.index(package)]

        for repository in self._repositories:
            package = repository.package(name, version)
            if package:
                self._packages.append(package)

                return package

        return None

    def find_packages(self,
                      name,
                      constraint=None) -> List['poetry.packages.Package']:
        for repository in self._repositories:
            packages = repository.find_packages(name, constraint)
            if packages:
                return packages

        return []

    def search(self, query, mode=BaseRepository.SEARCH_FULLTEXT):
        raise NotImplementedError()
