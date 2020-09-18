class BaseRepository(object):
    def __init__(self):
        self._packages = []

    @property
    def packages(self):
        return self._packages

    def has_package(self, package):
        raise NotImplementedError()

    def package(self, name, version, extras=None):
        raise NotImplementedError()

    def find_packages(self, dependency):
        raise NotImplementedError()

    def search(self, query):
        raise NotImplementedError()
