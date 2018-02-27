class BaseRepository:

    SEARCH_FULLTEXT = 0
    SEARCH_NAME = 1

    def __init__(self):
        self._packages = []

    @property
    def packages(self):
        return self._packages

    def has_package(self, package):
        raise NotImplementedError()

    def package(self, name, version):
        raise NotImplementedError()

    def find_packages(self, name, constraint=None):
        raise NotImplementedError()

    def search(self, query, mode=SEARCH_FULLTEXT):
        raise NotImplementedError()
