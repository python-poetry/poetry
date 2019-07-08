from poetry.semver import VersionRange
from poetry.semver import parse_constraint
from poetry.version.markers import parse_marker

from .package import Package
from .utils.utils import create_nested_marker


class ProjectPackage(Package):
    def __init__(self, name, version, pretty_version=None):
        super(ProjectPackage, self).__init__(name, version, pretty_version)

        self.build = None
        self.packages = []
        self.include = []
        self.exclude = []
        self.custom_urls = {}

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
        self._python_marker = parse_marker(
            create_nested_marker("python_version", self._python_constraint)
        )

    @property
    def urls(self):
        urls = super(ProjectPackage, self).urls

        urls.update(self.custom_urls)

        return urls

    def clone(self):  # type: () -> ProjectPackage
        package = super(ProjectPackage, self).clone()

        package.build = self.build
        package.packages = self.packages[:]
        package.include = self.include[:]
        package.exclude = self.exclude[:]

        return package
