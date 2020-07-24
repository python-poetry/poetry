from typing import TYPE_CHECKING

from .env_command import EnvCommand


if TYPE_CHECKING:
    from poetry.installation.installer import Installer
    from poetry.installation.installer import Optional


class InstallerCommand(EnvCommand):
    def __init__(self):
        self._installer = None  # type: Optional[Installer]

        super(InstallerCommand, self).__init__()

    def reset_poetry(self):
        super(InstallerCommand, self).reset_poetry()

        self._installer.set_package(self.poetry.package)
        self._installer.set_locker(self.poetry.locker)

    @property
    def installer(self):  # type: () -> Installer
        return self._installer

    def set_installer(self, installer):  # type: (Installer) -> None
        self._installer = installer
