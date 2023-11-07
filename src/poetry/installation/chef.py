from __future__ import annotations

import os
import tempfile

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

from build import BuildBackendException
from build import ProjectBuilder
from build.env import IsolatedEnv as BaseIsolatedEnv
from poetry.core.utils.helpers import temporary_directory
from pyproject_hooks import quiet_subprocess_runner  # type: ignore[import-untyped]

from poetry.utils._compat import decode
from poetry.utils.env import ephemeral_environment
from poetry.utils.helpers import extractall


if TYPE_CHECKING:
    from collections.abc import Collection

    from poetry.repositories import RepositoryPool
    from poetry.utils.cache import ArtifactCache
    from poetry.utils.env import Env


class ChefError(Exception): ...


class ChefBuildError(ChefError): ...


class ChefInstallError(ChefError):
    def __init__(self, requirements: Collection[str], output: str, error: str) -> None:
        message = "\n\n".join(
            (
                f"Failed to install {', '.join(requirements)}.",
                f"Output:\n{output}",
                f"Error:\n{error}",
            )
        )
        super().__init__(message)
        self._requirements = requirements

    @property
    def requirements(self) -> Collection[str]:
        return self._requirements


class IsolatedEnv(BaseIsolatedEnv):
    def __init__(self, env: Env, pool: RepositoryPool) -> None:
        self._env = env
        self._pool = pool

    @property
    def python_executable(self) -> str:
        return str(self._env.python)

    def make_extra_environ(self) -> dict[str, str]:
        path = os.environ.get("PATH")
        scripts_dir = str(self._env._bin_dir)
        return {
            "PATH": (
                os.pathsep.join([scripts_dir, path])
                if path is not None
                else scripts_dir
            )
        }

    def install(self, requirements: Collection[str]) -> None:
        from cleo.io.buffered_io import BufferedIO
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

        io = BufferedIO()
        installer = Installer(
            io,
            self._env,
            package,
            Locker(self._env.path.joinpath("poetry.lock"), {}),
            self._pool,
            Config.create(),
            InstalledRepository.load(self._env),
        )
        installer.update(True)
        if installer.run() != 0:
            raise ChefInstallError(requirements, io.fetch_output(), io.fetch_error())


class Chef:
    def __init__(
        self, artifact_cache: ArtifactCache, env: Env, pool: RepositoryPool
    ) -> None:
        self._env = env
        self._pool = pool
        self._artifact_cache = artifact_cache

    def prepare(
        self, archive: Path, output_dir: Path | None = None, *, editable: bool = False
    ) -> Path:
        if not self._should_prepare(archive):
            return archive

        if archive.is_dir():
            destination = output_dir or Path(tempfile.mkdtemp(prefix="poetry-chef-"))
            return self._prepare(archive, destination=destination, editable=editable)

        return self._prepare_sdist(archive, destination=output_dir)

    def _prepare(
        self, directory: Path, destination: Path, *, editable: bool = False
    ) -> Path:
        from subprocess import CalledProcessError

        with ephemeral_environment(self._env.python) as venv:
            env = IsolatedEnv(venv, self._pool)
            builder = ProjectBuilder.from_isolated_env(
                env, directory, runner=quiet_subprocess_runner
            )
            env.install(builder.build_system_requires)

            stdout = StringIO()
            error: Exception | None = None
            try:
                with redirect_stdout(stdout):
                    dist_format = "wheel" if not editable else "editable"
                    env.install(
                        builder.build_system_requires
                        | builder.get_requires_for_build(dist_format)
                    )
                    path = Path(
                        builder.build(
                            dist_format,
                            destination.as_posix(),
                        )
                    )
            except BuildBackendException as e:
                message_parts = [str(e)]
                if isinstance(e.exception, CalledProcessError):
                    text = e.exception.stderr or e.exception.stdout
                    if text is not None:
                        message_parts.append(decode(text))
                else:
                    message_parts.append(str(e.exception))

                error = ChefBuildError("\n\n".join(message_parts))

            if error is not None:
                raise error from None

            return path

    def _prepare_sdist(self, archive: Path, destination: Path | None = None) -> Path:
        from poetry.core.packages.utils.link import Link

        suffix = archive.suffix
        zip = suffix == ".zip"

        with temporary_directory() as tmp_dir:
            archive_dir = Path(tmp_dir)
            extractall(source=archive, dest=archive_dir, zip=zip)

            elements = list(archive_dir.glob("*"))

            if len(elements) == 1 and elements[0].is_dir():
                sdist_dir = elements[0]
            else:
                sdist_dir = archive_dir / archive.name.rstrip(suffix)
                if not sdist_dir.is_dir():
                    sdist_dir = archive_dir

            if destination is None:
                destination = self._artifact_cache.get_cache_directory_for_link(
                    Link(archive.as_uri())
                )

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
