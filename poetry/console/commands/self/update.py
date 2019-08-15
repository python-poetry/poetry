import hashlib
import os
import shutil
import subprocess
import sys
import tarfile

from functools import cmp_to_key
from gzip import GzipFile

try:
    from urllib.error import HTTPError
    from urllib.request import urlopen
except ImportError:
    from urllib2 import HTTPError
    from urllib2 import urlopen

from ..command import Command


class SelfUpdateCommand(Command):
    """
    Updates poetry to the latest version.

    self:update
        { version? : The version to update to. }
        { --preview : Install prereleases. }
    """

    BASE_URL = "https://github.com/sdispater/poetry/releases/download"

    @property
    def home(self):
        from poetry.utils._compat import Path
        from poetry.utils.appdirs import expanduser

        home = Path(expanduser("~"))

        return home / ".poetry"

    @property
    def lib(self):
        return self.home / "lib"

    @property
    def lib_backup(self):
        return self.home / "lib-backup"

    def handle(self):
        from poetry.__version__ import __version__
        from poetry.repositories.pypi_repository import PyPiRepository
        from poetry.semver import Version
        from poetry.utils._compat import Path
        from poetry.utils._compat import decode

        current = Path(__file__)
        try:
            current.relative_to(self.home)
        except ValueError:
            raise RuntimeError(
                "Poetry was not installed with the recommended installer. "
                "Cannot update automatically."
            )

        version = self.argument("version")
        if not version:
            version = ">=" + __version__

        repo = PyPiRepository(fallback=False)
        packages = repo.find_packages(
            "poetry", version, allow_prereleases=self.option("preview")
        )
        if not packages:
            self.line("No release found for the specified version")
            return

        packages.sort(
            key=cmp_to_key(
                lambda x, y: 0
                if x.version == y.version
                else int(x.version < y.version or -1)
            )
        )

        release = None
        for package in packages:
            if package.is_prerelease():
                if self.option("preview"):
                    release = package

                    break

                continue

            release = package

            break

        if release is None:
            self.line("No new release found")
            return

        if release.version == Version.parse(__version__):
            self.line("You are using the latest version")
            return

        try:
            self.update(release)
        except subprocess.CalledProcessError as e:
            self.line("")
            self.output.block(
                [
                    "[CalledProcessError]",
                    "An error has occured: {}".format(str(e)),
                    decode(e.output),
                ],
                style="error",
            )

            return e.returncode

    def update(self, release):
        version = release.version
        self.line("Updating to <info>{}</info>".format(version))

        if self.lib_backup.exists():
            shutil.rmtree(str(self.lib_backup))

        # Backup the current installation
        if self.lib.exists():
            shutil.copytree(str(self.lib), str(self.lib_backup))
            shutil.rmtree(str(self.lib))

        try:
            self._update(version)
        except Exception:
            if not self.lib_backup.exists():
                raise

            shutil.copytree(str(self.lib_backup), str(self.lib))
            shutil.rmtree(str(self.lib_backup))

            raise
        finally:
            if self.lib_backup.exists():
                shutil.rmtree(str(self.lib_backup))

        self.line("")
        self.line("")
        self.line(
            "<info>Poetry</info> (<comment>{}</comment>) is installed now. Great!".format(
                version
            )
        )

    def _update(self, version):
        from poetry.utils.helpers import temporary_directory

        platform = sys.platform
        if platform == "linux2":
            platform = "linux"

        checksum = "poetry-{}-{}.sha256sum".format(version, platform)

        try:
            r = urlopen(self.BASE_URL + "/{}/{}".format(version, checksum))
        except HTTPError as e:
            if e.code == 404:
                raise RuntimeError("Could not find {} file".format(checksum))

            raise

        checksum = r.read().decode()

        # We get the payload from the remote host
        name = "poetry-{}-{}.tar.gz".format(version, platform)
        try:
            r = urlopen(self.BASE_URL + "/{}/{}".format(version, name))
        except HTTPError as e:
            if e.code == 404:
                raise RuntimeError("Could not find {} file".format(name))

            raise

        meta = r.info()
        size = int(meta["Content-Length"])
        current = 0
        block_size = 8192

        bar = self.progress_bar(max=size)
        bar.set_format(" - Downloading <info>{}</> <comment>%percent%%</>".format(name))
        bar.start()

        sha = hashlib.sha256()
        with temporary_directory(prefix="poetry-updater-") as dir_:
            tar = os.path.join(dir_, name)
            with open(tar, "wb") as f:
                while True:
                    buffer = r.read(block_size)
                    if not buffer:
                        break

                    current += len(buffer)
                    f.write(buffer)
                    sha.update(buffer)

                    bar.set_progress(current)

            bar.finish()

            # Checking hashes
            if checksum != sha.hexdigest():
                raise RuntimeError(
                    "Hashes for {} do not match: {} != {}".format(
                        name, checksum, sha.hexdigest()
                    )
                )

            gz = GzipFile(tar, mode="rb")
            try:
                with tarfile.TarFile(tar, fileobj=gz, format=tarfile.PAX_FORMAT) as f:
                    f.extractall(str(self.lib))
            finally:
                gz.close()

    def process(self, *args):
        return subprocess.check_output(list(args), stderr=subprocess.STDOUT)

    def _bin_path(self, base_path, bin):
        if sys.platform == "win32":
            return (base_path / "Scripts" / bin).with_suffix(".exe")

        return base_path / "bin" / bin
