class BaseInstaller:

    def install(self, package):
        raise NotImplementedError

    def update(self, source, target):
        raise NotImplementedError

    def remove(self, package):
        raise NotImplementedError
