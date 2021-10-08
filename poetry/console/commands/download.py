from cleo.helpers import option

from .installer_command import InstallerCommand


class DownloadCommand(InstallerCommand):

    name = "download"
    description = "Downloads dependencies into local folder."

    arguments = []

    options = [option("folder", None, "Folder to download dependencies to.")]

    help = """Some help"""

    def handle(self) -> int:
        return self._installer.download()
