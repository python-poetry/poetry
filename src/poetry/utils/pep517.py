from __future__ import annotations

import logging
import sys

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import build
import pep517  # type: ignore[import]

from cleo.io.null_io import NullIO
from poetry.core.packages.project_package import ProjectPackage

from poetry.config.config import Config
from poetry.factory import Factory
from poetry.installation import Installer
from poetry.packages.locker import NullLocker
from poetry.repositories import Pool
from poetry.repositories.pypi_repository import PyPiRepository
from poetry.utils.dependency_specification import pep508_to_dependency_specification
from poetry.utils.env import ephemeral_environment


if TYPE_CHECKING:
    from collections.abc import Iterator

    from poetry.utils.env import Env


logger = logging.getLogger(__name__)


@contextmanager
def pep517_builder_environment(
    source: Path, env: Env | None = None
) -> Iterator[tuple[Env, build.ProjectBuilder]]:
    with ephemeral_environment(executable=env.python if env else None) as env:
        builder = build.ProjectBuilder(
            srcdir=str(source),
            scripts_dir=None,
            python_executable=env.python,
            runner=pep517.quiet_subprocess_runner,
        )

        root = ProjectPackage("root", "0.0.0")
        root.python_versions = (
            f"{sys.version_info.major}.{sys.version_info.minor}."
            f"{sys.version_info.micro}"
        )

        installer = Installer(
            NullIO(),
            env,
            root,
            NullLocker(Path(env.path).joinpath("poetry.lock"), {}),
            Pool([PyPiRepository()]),
            Config.create(),
        )

        def _add_dependency(_requirement: str) -> None:
            spec = pep508_to_dependency_specification(_requirement) or {
                "name": _requirement,
                "version": "*",
            }
            root.add_dependency(Factory.create_dependency(spec.pop("name"), spec))

        for requirement in builder.build_system_requires:
            _add_dependency(requirement)
        installer.run()

        for requirement in builder.get_requires_for_build("wheel"):
            _add_dependency(requirement)
        installer.run()

        yield env, builder
