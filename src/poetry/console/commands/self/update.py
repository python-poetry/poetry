import os
import shutil
import site

from functools import cmp_to_key
from pathlib import Path
from typing import TYPE_CHECKING

from cleo.helpers import argument
from cleo.helpers import option

from poetry.console.commands.command import Command


if TYPE_CHECKING:
    from poetry.core.packages.package import Package
    from poetry.core.semver.version import Version

    from poetry.repositories.pool import Pool


class SelfUpdateCommand(Command):

    name = "self update"
    description = "Updates Poetry to the latest version."

    arguments = [argument("version", "The version to update to.", optional=True)]
    options = [
        option("preview", None, "Allow the installation of pre-release versions."),
        option(
            "dry-run",
            None,
            "Output the operations but do not execute anything "
            "(implicitly enables --verbose).",
        ),
    ]

    _data_dir = None
    _bin_dir = None
    _pool = None

    @property
    def data_dir(self) -> Path:
        if self._data_dir is not None:
            return self._data_dir

        from poetry.locations import data_dir

        self._data_dir = data_dir()

        return self._data_dir

    @property
    def bin_dir(self) -> Path:
        if self._data_dir is not None:
            return self._data_dir

        from poetry.utils._compat import WINDOWS

        if os.getenv("POETRY_HOME"):
            return Path(os.getenv("POETRY_HOME"), "bin").expanduser()

        user_base = site.getuserbase()

        if WINDOWS:
            bin_dir = os.path.join(user_base, "Scripts")
        else:
            bin_dir = os.path.join(user_base, "bin")

        self._bin_dir = Path(bin_dir)

        return self._bin_dir

    @property
    def pool(self) -> "Pool":
        if self._pool is not None:
            return self._pool

        from poetry.repositories.pool import Pool
        from poetry.repositories.pypi_repository import PyPiRepository

        pool = Pool()
        pool.add_repository(PyPiRepository())

        return pool

    def handle(self) -> int:
        from poetry.core.packages.dependency import Dependency
        from poetry.core.semver.version import Version

        from poetry.__version__ import __version__

        version = self.argument("version")
        if not version:
            version = ">=" + __version__

        repo = self.pool.repositories[0]
        packages = repo.find_packages(
            Dependency("poetry", version, allows_prereleases=self.option("preview"))
        )
        if not packages:
            self.line("No release found for the specified version")
            return 1

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
            return 1

        if release.version == Version.parse(__version__):
            self.line("You are using the latest version")
            return 0

        self.line(f"Updating <c1>Poetry</c1> to <c2>{release.version}</c2>")
        self.line("")

        self.update(release)

        self.line("")
        self.line(
            f"<c1>Poetry</c1> (<c2>{release.version}</c2>) is installed now. Great!"
        )

        return 0

    def update(self, release: "Package") -> None:
        from poetry.utils.env import EnvManager

        version = release.version

        env = EnvManager.get_system_env(naive=True)

        # We can't use is_relative_to() since it's only available in Python 3.9+
        try:
            env.path.relative_to(self.data_dir)
        except ValueError:
            # Poetry was not installed using the recommended installer
            from poetry.console.exceptions import PoetrySimpleConsoleException

            raise PoetrySimpleConsoleException(
                "Poetry was not installed with the recommended installer, "
                "so it cannot be updated automatically."
            )

        self._update(version)
        self._make_bin()

    def _update(self, version: "Version") -> None:
        from poetry.core.packages.dependency import Dependency
        from poetry.core.packages.project_package import ProjectPackage

        from poetry.config.config import Config
        from poetry.installation.installer import Installer
        from poetry.packages.locker import NullLocker
        from poetry.repositories.installed_repository import InstalledRepository
        from poetry.utils.env import EnvManager

        env = EnvManager.get_system_env(naive=True)
        installed = InstalledRepository.load(env)

        root = ProjectPackage("poetry-updater", "0.0.0")
        root.python_versions = ".".join(str(c) for c in env.version_info[:3])
        root.add_dependency(Dependency("poetry", version.text))

        installer = Installer(
            self.io,
            env,
            root,
            NullLocker(self.data_dir.joinpath("poetry.lock"), {}),
            self.pool,
            Config(),
            installed=installed,
        )
        installer.update(True)
        installer.dry_run(self.option("dry-run"))
        installer.run()

    def _make_bin(self) -> None:
        from poetry.utils._compat import WINDOWS

        self.line("")
        self.line("Updating the <c1>poetry</c1> script")

        self.bin_dir.mkdir(parents=True, exist_ok=True)

        script = "poetry"
        target_script = "venv/bin/poetry"
        if WINDOWS:
            script = "poetry.exe"
            target_script = "venv/Scripts/poetry.exe"

        if self.bin_dir.joinpath(script).exists():
            self.bin_dir.joinpath(script).unlink()

        try:
            self.bin_dir.joinpath(script).symlink_to(
                self.data_dir.joinpath(target_script)
            )
        except OSError:
            # This can happen if the user
            # does not have the correct permission on Windows
            shutil.copy(
                self.data_dir.joinpath(target_script), self.bin_dir.joinpath(script)
            )
