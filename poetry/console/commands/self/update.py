import os
import shutil
import subprocess
import sys

from email.parser import Parser

from functools import cmp_to_key

from ..command import Command


class SelfUpdateCommand(Command):
    """
    Updates poetry to the latest version.

    self:update
        { version? : The version to update to. }
        { --preview : Install prereleases. }
    """

    def handle(self):
        from poetry.__version__ import __version__
        from poetry.repositories.pypi_repository import PyPiRepository
        from poetry.semver import Version
        from poetry.utils._compat import Path
        from poetry.utils._compat import decode
        from poetry.utils.appdirs import expanduser

        home = Path(expanduser("~"))
        poetry_home = home / ".poetry"

        current_file = Path(__file__)

        try:
            current_file.relative_to(poetry_home)
        except ValueError:
            raise RuntimeError(
                "Poetry has not been installed with the recommended installer. Aborting."
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
        from poetry.utils._compat import Path
        from poetry.utils.appdirs import expanduser

        home = Path(expanduser("~"))
        poetry_home = home / ".poetry"
        poetry_bin = poetry_home / "bin"
        poetry_lib = poetry_home / "lib"
        poetry_lib_backup = poetry_home / "lib.backup"

        version = release.version
        self.line("Updating to <info>{}</info>".format(version))

        if poetry_lib.exists():
            # Backing up the current lib directory
            if poetry_lib_backup.exists():
                shutil.rmtree(str(poetry_lib_backup))

            shutil.copytree(str(poetry_lib), str(poetry_lib_backup))
            shutil.rmtree(str(poetry_lib))

        try:
            self._update(release, poetry_lib)
        except Exception as e:
            # Reverting changes
            if poetry_lib_backup.exists():
                if poetry_lib.exists():
                    shutil.rmtree(str(poetry_lib))

                shutil.copytree(str(poetry_lib_backup), str(poetry_lib))

            message = (
                "An error occured when updating Poetry. "
                "The changes have been rolled back."
            )

            if self.output.is_debug():
                message += " Original error: {}".format(e)

            raise RuntimeError(message)
        finally:
            if poetry_lib_backup.exists():
                shutil.rmtree(str(poetry_lib_backup))

        self.line("")
        self.line(
            "<info>Poetry</> (<comment>{}</>) "
            "is installed now. Great!".format(version)
        )

    def _update(self, release, lib):
        from poetry.utils._compat import Path
        from poetry.utils.helpers import temporary_directory

        with temporary_directory(prefix="poetry-update-") as temp_dir:
            temp_dir = Path(temp_dir)
            dist = temp_dir / "dist"
            self.line("  - Getting dependencies")
            self.process(
                sys.executable,
                "-m",
                "pip",
                "install",
                "-U",
                "poetry=={}".format(release.version),
                "--target",
                str(dist),
            )

            self.line("  - Vendorizing dependencies")

            poetry_dir = dist / "poetry"
            vendor_dir = poetry_dir / "_vendor"

            # Everything, except poetry itself, should
            # be put in the _vendor directory
            for file in dist.glob("*"):
                if file.name.startswith("poetry"):
                    continue

                dest = vendor_dir / file.name
                if file.is_dir():
                    shutil.copytree(str(file), str(dest))
                    shutil.rmtree(str(file))
                else:
                    shutil.copy(str(file), str(dest))
                    os.unlink(str(file))

            shutil.copytree(dist, str(lib))

    def process(self, *args):
        return subprocess.check_output(list(args), stderr=subprocess.STDOUT)

    def _bin_path(self, base_path, bin):
        if sys.platform == "win32":
            return (base_path / "Scripts" / bin).with_suffix(".exe")

        return base_path / "bin" / bin
