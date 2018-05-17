from .package import Package


class ProjectPackage(Package):

    def is_root(self):
        return True

    def to_dependency(self):
        dependency = super(ProjectPackage, self).to_dependency()

        dependency.is_root = True

        return dependency
