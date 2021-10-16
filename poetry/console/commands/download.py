from cleo.helpers import option

from .installer_command import InstallerCommand

DOWNLOAD_FOLDER_DEFAULT = ".poetry_locked"


class DownloadCommand(InstallerCommand):

    name = "download"
    description = "Downloads the dependencies into a local folder."

    arguments = []

    options = [option("folder",
                      None,
                      "Folder to download dependencies to.",
                      flag=False,
                      default=DOWNLOAD_FOLDER_DEFAULT)]

    help = """The <info>download</info> command downloads the dependencies into a local folder 
    so later you can install them from this folder. These dependencies won't been installed.
    Poetry won't try to update the dependencies or modify poetry.lock file - just make sure the 
    packages are saved locally. 
    """

    def handle(self) -> int:
        self._installer.offline_folder(self.option("folder"))
        return self._installer.download()
