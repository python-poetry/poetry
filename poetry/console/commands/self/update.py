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
        from poetry.utils._compat import decode

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
        from poetry.utils.helpers import temporary_directory

        version = release.version
        self.line("Updating to <info>{}</info>".format(version))

        prefix = sys.prefix
        base_prefix = getattr(sys, "base_prefix", None)
        real_prefix = getattr(sys, "real_prefix", None)

        prefix_poetry = self._bin_path(Path(prefix), "poetry")
        if prefix_poetry.exists():
            pip = self._bin_path(prefix_poetry.parent.parent, "pip").resolve()
        elif (
            base_prefix
            and base_prefix != prefix
            and self._bin_path(Path(base_prefix), "poetry").exists()
        ):
            pip = self._bin_path(Path(base_prefix), "pip")
        elif real_prefix:
            pip = self._bin_path(Path(real_prefix), "pip")
        else:
            pip = self._bin_path(Path(prefix), "pip")

            if not pip.exists():
                raise RuntimeError("Unable to determine poetry's path")

        with temporary_directory(prefix="poetry-update-") as temp_dir:
            temp_dir = Path(temp_dir)
            dist = temp_dir / "dist"
            self.line("  - Getting dependencies")
            self.process(
                str(pip),
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

            wheel_data = dist / "poetry-{}.dist-info".format(version) / "WHEEL"
            with wheel_data.open() as f:
                wheel_data = Parser().parsestr(f.read())

            tag = wheel_data["Tag"]

            # Repack everything and install
            self.line("  - Updating <info>poetry</info>")

            shutil.make_archive(
                str(temp_dir / "poetry-{}-{}".format(version, tag)),
                format="zip",
                root_dir=str(dist),
            )

            os.rename(
                str(temp_dir / "poetry-{}-{}.zip".format(version, tag)),
                str(temp_dir / "poetry-{}-{}.whl".format(version, tag)),
            )

            self.process(
                str(pip),
                "install",
                "--upgrade",
                "--no-deps",
                str(temp_dir / "poetry-{}-{}.whl".format(version, tag)),
            )

            self.line("")
            self.line(
                "<info>poetry</> (<comment>{}</>) "
                "successfully installed!".format(version)
            )

    def process(self, *args):
        return subprocess.check_output(list(args), stderr=subprocess.STDOUT)

    def _bin_path(self, base_path, bin):
        if sys.platform == "win32":
            return (base_path / "Scripts" / bin).with_suffix(".exe")

        return base_path / "bin" / bin
