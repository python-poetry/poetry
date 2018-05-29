from .base_installer import BaseInstaller


class NoopInstaller(BaseInstaller):
    def __init__(self):
        self._installs = []
        self._updates = []
        self._removals = []

    @property
    def installs(self):
        return self._installs

    @property
    def updates(self):
        return self._updates

    @property
    def removals(self):
        return self._removals

    def install(self, package):
        self._installs.append(package)

    def update(self, source, target):
        self._updates.append((source, target))

    def remove(self, package):
        self._removals.append(package)
