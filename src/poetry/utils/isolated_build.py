from __future__ import annotations

import os

from contextlib import contextmanager
from contextlib import redirect_stdout
from io import StringIO
from typing import TYPE_CHECKING
from typing import Collection
from typing import Iterator

from build.env import IsolatedEnv as BaseIsolatedEnv

from poetry.utils.env import Env
from poetry.utils.env import EnvManager
from poetry.utils.env import ephemeral_environment


if TYPE_CHECKING:
    from pathlib import Path

    from build import ProjectBuilder

    from poetry.repositories import RepositoryPool


class IsolatedBuildBaseError(Exception): ...


class IsolatedBuildError(IsolatedBuildBaseError): ...


class IsolatedBuildInstallError(IsolatedBuildBaseError):
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
            raise IsolatedBuildInstallError(
                requirements, io.fetch_output(), io.fetch_error()
            )


@contextmanager
def isolated_builder(
    source: Path,
    distribution: str = "wheel",
    python_executable: Path | None = None,
    pool: RepositoryPool | None = None,
) -> Iterator[ProjectBuilder]:
    from build import ProjectBuilder
    from pyproject_hooks import quiet_subprocess_runner  # type: ignore[import-untyped]

    from poetry.factory import Factory

    # we recreate the project's Poetry instance in order to retrieve the correct repository pool
    # when a pool is not provided
    pool = pool or Factory().create_poetry().pool

    python_executable = (
        python_executable or EnvManager.get_system_env(naive=True).python
    )

    with ephemeral_environment(
        executable=python_executable,
        flags={"no-pip": True, "no-setuptools": True, "no-wheel": True},
    ) as venv:
        env = IsolatedEnv(venv, pool)
        stdout = StringIO()

        builder = ProjectBuilder.from_isolated_env(
            env, source, runner=quiet_subprocess_runner
        )

        with redirect_stdout(stdout):
            env.install(builder.build_system_requires)

            # we repeat the build system requirements to avoid poetry installer from removing them
            env.install(
                builder.build_system_requires
                | builder.get_requires_for_build(distribution)
            )

            yield builder
