from poetry.semver import VersionRange
from poetry.semver import parse_constraint

from .package import Package


class ProjectPackage(Package):
    def __init__(self, name, version, pretty_version=None):
        super(ProjectPackage, self).__init__(name, version, pretty_version)

        self.build = None
        self.packages = []
        self.include = []
        self.exclude = []

        if self._python_versions == "*":
            self._python_constraint = parse_constraint("~2.7 || >=3.4")

    def is_root(self):
        return True

    def to_dependency(self):
        dependency = super(ProjectPackage, self).to_dependency()

        dependency.is_root = True

        return dependency

    @property
    def python_versions(self):
        return self._python_versions

    @python_versions.setter
    def python_versions(self, value):
        self._python_versions = value
        if value == "*" or value == VersionRange():
            value = "~2.7 || >=3.4"

        self._python_constraint = parse_constraint(value)
