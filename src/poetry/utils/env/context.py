from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Iterator

from poetry.core.utils.helpers import temporary_directory

from poetry.utils.env import Env
from poetry.utils.env import EnvManager
from poetry.utils.env import VirtualEnv
from poetry.utils.pip import Pip


if TYPE_CHECKING:
    from cleo.io.io import IO
    from poetry.core.poetry import Poetry as CorePoetry


@contextmanager
def ephemeral_environment(
    executable: str | Path | None = None,
    flags: dict[str, bool] | None = None,
) -> Iterator[VirtualEnv]:
    with temporary_directory() as tmp_dir:
        # TODO: cache PEP 517 build environment corresponding to each project venv
        venv_dir = Path(tmp_dir) / ".venv"
        EnvManager.build_venv(
            path=venv_dir.as_posix(),
            executable=executable,
            flags=flags,
        )
        yield VirtualEnv(venv_dir, venv_dir)


@contextmanager
def build_environment(
    poetry: CorePoetry, env: Env | None = None, io: IO | None = None
) -> Iterator[Env]:
    """
    If a build script is specified for the project, there could be additional build
    time dependencies, eg: cython, setuptools etc. In these cases, we create an
    ephemeral build environment with all requirements specified under
    `build-system.requires` and return this. Otherwise, the given default project
    environment is returned.
    """
    if not env or poetry.package.build_script:
        with ephemeral_environment(executable=env.python if env else None) as venv:
            overwrite = (
                io is not None and io.output.is_decorated() and not io.is_debug()
            )

            if io:
                if not overwrite:
                    io.write_error_line("")

                requires = [
                    f"<c1>{requirement}</c1>"
                    for requirement in poetry.pyproject.build_system.requires
                ]

                io.overwrite_error(
                    "<b>Preparing</b> build environment with build-system requirements"
                    f" {', '.join(requires)}"
                )

            pip = Pip(target_env=venv)
            pip.install_requirements(poetry.pyproject.build_system.requires)

            if overwrite:
                assert io is not None
                io.write_error_line("")

            yield venv
    else:
        yield env
