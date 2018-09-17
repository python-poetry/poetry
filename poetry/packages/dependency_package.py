from .package import Package


class DependencyPackage:
    def __init__(self, dependency, package):
        self._dependency = dependency
        self._package = package

    @property
    def dependency(self):
        return self._dependency

    @property
    def package(self):
        return self._package

    def __getattr__(self, name):
        return getattr(self._package, name)

    def __str__(self):
        return str(self._package)

    def __repr__(self):
        return repr(self._package)

    def __hash__(self):
        return hash(self._package)

    def __eq__(self, other):
        if isinstance(other, DependencyPackage):
            other = other.package

        return self._package == other
