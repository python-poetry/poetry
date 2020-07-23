from typing import TYPE_CHECKING

from .env_command import EnvCommand


if TYPE_CHECKING:
    from poetry.installation.installer import Installer


class InstallerCommand(EnvCommand):
    def __init__(self):
        self._installer = None

        super(InstallerCommand, self).__init__()

    @property
    def installer(self):  # type: () -> Installer
        return self._installer

    def set_installer(self, installer):  # type: (Installer) -> None
        self._installer = installer
