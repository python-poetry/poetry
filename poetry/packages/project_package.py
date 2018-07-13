from .package import Package


class ProjectPackage(Package):
    def __init__(self, name, version, pretty_version=None):
        super(ProjectPackage, self).__init__(name, version, pretty_version)

        self.build = None
        self.packages = []
        self.include = []
        self.exclude = []

    def is_root(self):
        return True

    def to_dependency(self):
        dependency = super(ProjectPackage, self).to_dependency()

        dependency.is_root = True

        return dependency
