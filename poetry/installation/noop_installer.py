from .base_installer import BaseInstaller


class NoopInstaller(BaseInstaller):

    def install(self, package) -> None:
        pass

    def update(self, source, target) -> None:
        pass

    def remove(self, package) -> None:
        pass
