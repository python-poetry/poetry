from __future__ import annotations

import hashlib
import json
import tarfile
import tempfile
import zipfile

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Callable
from typing import Collection

from build import BuildBackendException
from build import ProjectBuilder
from build.env import IsolatedEnv as BaseIsolatedEnv
from poetry.core.utils.helpers import temporary_directory
from pyproject_hooks import quiet_subprocess_runner  # type: ignore[import]

from poetry.installation.chooser import InvalidWheelName
from poetry.installation.chooser import Wheel
from poetry.utils.env import ephemeral_environment


if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from poetry.core.packages.utils.link import Link

    from poetry.config.config import Config
    from poetry.repositories import RepositoryPool
    from poetry.utils.env import Env


class ChefError(Exception):
    ...


class ChefBuildError(ChefError):
    ...


class IsolatedEnv(BaseIsolatedEnv):
    def __init__(self, env: Env, pool: RepositoryPool) -> None:
        self._env = env
        self._pool = pool

    @property
    def executable(self) -> str:
        return str(self._env.python)

    @property
    def scripts_dir(self) -> str:
        return str(self._env._bin_dir)

    def install(self, requirements: Collection[str]) -> None:
        from cleo.io.null_io import NullIO
        from poetry.core.packages.dependency import Dependency
        from poetry.core.packages.project_package import ProjectPackage

        from poetry.config.config import Config
        from poetry.installation.installer import Installer
        from poetry.packages.locker import Locker
        from poetry.repositories.installed_repository import InstalledRepository

        # We build Poetry dependencies from the requirements
        package = ProjectPackage("__root__", "0.0.0")
        package.python_versions = ".".join(str(v) for v in self._env.version_info[:3])
        for requirement in requirements:
            dependency = Dependency.create_from_pep_508(requirement)
            package.add_dependency(dependency)

        installer = Installer(
            NullIO(),
            self._env,
            package,
            Locker(self._env.path.joinpath("poetry.lock"), {}),
            self._pool,
            Config.create(),
            InstalledRepository.load(self._env),
        )
        installer.update(True)
        installer.run()


class Chef:
    def __init__(self, config: Config, env: Env, pool: RepositoryPool) -> None:
        self._env = env
        self._pool = pool
        self._cache_dir = (
            Path(config.get("cache-dir")).expanduser().joinpath("artifacts")
        )

    def prepare(
        self, archive: Path, output_dir: Path | None = None, *, editable: bool = False
    ) -> Path:
        if not self._should_prepare(archive):
            return archive

        if archive.is_dir():
            tmp_dir = tempfile.mkdtemp(prefix="poetry-chef-")

            return self._prepare(archive, Path(tmp_dir), editable=editable)

        return self._prepare_sdist(archive, destination=output_dir)

    def _prepare(
        self, directory: Path, destination: Path, *, editable: bool = False
    ) -> Path:
        from subprocess import CalledProcessError

        with ephemeral_environment(self._env.python) as venv:
            env = IsolatedEnv(venv, self._pool)
            builder = ProjectBuilder(
                directory,
                python_executable=env.executable,
                scripts_dir=env.scripts_dir,
                runner=quiet_subprocess_runner,
            )
            env.install(builder.build_system_requires)

            stdout = StringIO()
            error: Exception | None = None
            try:
                with redirect_stdout(stdout):
                    env.install(
                        builder.build_system_requires
                        | builder.get_requires_for_build("wheel")
                    )
                    path = Path(
                        builder.build(
                            "wheel" if not editable else "editable",
                            destination.as_posix(),
                        )
                    )
            except BuildBackendException as e:
                message_parts = [str(e)]
                if isinstance(e.exception, CalledProcessError) and (
                    e.exception.stdout is not None or e.exception.stderr is not None
                ):
                    message_parts.append(
                        e.exception.stderr.decode()
                        if e.exception.stderr is not None
                        else e.exception.stdout.decode()
                    )

                error = ChefBuildError("\n\n".join(message_parts))

            if error is not None:
                raise error from None

            return path

    def _prepare_sdist(self, archive: Path, destination: Path | None = None) -> Path:
        from poetry.core.packages.utils.link import Link

        suffix = archive.suffix
        context: Callable[
            [str], AbstractContextManager[zipfile.ZipFile | tarfile.TarFile]
        ]
        if suffix == ".zip":
            context = zipfile.ZipFile
        else:
            context = tarfile.open

        with temporary_directory() as tmp_dir:
            with context(archive.as_posix()) as archive_archive:
                archive_archive.extractall(tmp_dir)

            archive_dir = Path(tmp_dir)

            elements = list(archive_dir.glob("*"))

            if len(elements) == 1 and elements[0].is_dir():
                sdist_dir = elements[0]
            else:
                sdist_dir = archive_dir / archive.name.rstrip(suffix)
                if not sdist_dir.is_dir():
                    sdist_dir = archive_dir

            if destination is None:
                destination = self.get_cache_directory_for_link(Link(archive.as_uri()))

            destination.mkdir(parents=True, exist_ok=True)

            return self._prepare(
                sdist_dir,
                destination,
            )

    def _should_prepare(self, archive: Path) -> bool:
        return archive.is_dir() or not self._is_wheel(archive)

    @classmethod
    def _is_wheel(cls, archive: Path) -> bool:
        return archive.suffix == ".whl"

    def get_cached_archive_for_link(self, link: Link) -> Path | None:
        archives = self.get_cached_archives_for_link(link)
        if not archives:
            return None

        candidates: list[tuple[float | None, Path]] = []
        for archive in archives:
            if archive.suffix != ".whl":
                candidates.append((float("inf"), archive))
                continue

            try:
                wheel = Wheel(archive.name)
            except InvalidWheelName:
                continue

            if not wheel.is_supported_by_environment(self._env):
                continue

            candidates.append(
                (wheel.get_minimum_supported_index(self._env.supported_tags), archive),
            )

        if not candidates:
            return None

        return min(candidates)[1]

    def get_cached_archives_for_link(self, link: Link) -> list[Path]:
        cache_dir = self.get_cache_directory_for_link(link)

        archive_types = ["whl", "tar.gz", "tar.bz2", "bz2", "zip"]
        paths = []
        for archive_type in archive_types:
            for archive in cache_dir.glob(f"*.{archive_type}"):
                paths.append(Path(archive))

        return paths

    def get_cache_directory_for_link(self, link: Link) -> Path:
        key_parts = {"url": link.url_without_fragment}

        if link.hash_name is not None and link.hash is not None:
            key_parts[link.hash_name] = link.hash

        if link.subdirectory_fragment:
            key_parts["subdirectory"] = link.subdirectory_fragment

        key_parts["interpreter_name"] = self._env.marker_env["interpreter_name"]
        key_parts["interpreter_version"] = "".join(
            self._env.marker_env["interpreter_version"].split(".")[:2]
        )

        key = hashlib.sha256(
            json.dumps(
                key_parts, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("ascii")
        ).hexdigest()

        split_key = [key[:2], key[2:4], key[4:6], key[6:]]

        return self._cache_dir.joinpath(*split_key)
