from __future__ import annotations

import tempfile

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from zipfile import is_zipfile

from poetry.core.packages.utils.utils import splitext

from poetry.utils.helpers import extractall
from poetry.utils.isolated_build import isolated_builder


if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence

    from build import DistributionType
    from poetry.core.packages.dependency import Dependency

    from poetry.repositories import RepositoryPool
    from poetry.utils.cache import ArtifactCache
    from poetry.utils.env import Env


class ChefError(Exception): ...


class Chef:
    def __init__(
        self, artifact_cache: ArtifactCache, env: Env, pool: RepositoryPool
    ) -> None:
        self._env = env
        self._pool = pool
        self._artifact_cache = artifact_cache

    def prepare(
        self,
        archive: Path,
        output_dir: Path | None = None,
        *,
        editable: bool = False,
        config_settings: Mapping[str, str | Sequence[str]] | None = None,
        build_constraints: list[Dependency] | None = None,
    ) -> Path:
        if not self._should_prepare(archive):
            return archive

        if archive.is_dir():
            destination = output_dir or Path(tempfile.mkdtemp(prefix="poetry-chef-"))
            return self._prepare(
                archive,
                destination=destination,
                editable=editable,
                config_settings=config_settings,
                build_constraints=build_constraints,
            )

        return self._prepare_sdist(
            archive,
            destination=output_dir,
            config_settings=config_settings,
            build_constraints=build_constraints,
        )

    def _prepare(
        self,
        directory: Path,
        destination: Path,
        *,
        editable: bool = False,
        config_settings: Mapping[str, str | Sequence[str]] | None = None,
        build_constraints: list[Dependency] | None = None,
    ) -> Path:
        distribution: DistributionType = "editable" if editable else "wheel"
        with isolated_builder(
            source=directory,
            distribution=distribution,
            python_executable=self._env.python,
            pool=self._pool,
            build_constraints=build_constraints,
        ) as builder:
            return Path(
                builder.build(
                    distribution,
                    destination.as_posix(),
                    config_settings=config_settings,
                )
            )

    def _prepare_sdist(
        self,
        archive: Path,
        destination: Path | None = None,
        config_settings: Mapping[str, str | Sequence[str]] | None = None,
        build_constraints: list[Dependency] | None = None,
    ) -> Path:
        from poetry.core.packages.utils.link import Link

        _, suffix = splitext(archive)
        zip = suffix == ".zip"

        with TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
            archive_dir = Path(tmp_dir)
            extractall(source=archive, dest=archive_dir, zip=zip)

            elements = list(archive_dir.glob("*"))

            if len(elements) == 1 and elements[0].is_dir():
                sdist_dir = elements[0]
            else:
                sdist_dir = archive_dir / archive.name.removesuffix(suffix)
                if not sdist_dir.is_dir():
                    sdist_dir = archive_dir

            if destination is None:
                destination = self._artifact_cache.get_cache_directory_for_link(
                    Link(archive.as_uri())
                )

            destination.mkdir(parents=True, exist_ok=True)

            # Keep the wheel out of cache lookups until the backend finishes.
            with TemporaryDirectory(dir=destination, prefix=".poetry-wheel-") as stage:
                staging_dir = Path(stage).resolve()
                wheel = self._prepare(
                    sdist_dir,
                    staging_dir,
                    config_settings=config_settings,
                    build_constraints=build_constraints,
                ).resolve()
                if not wheel.is_relative_to(staging_dir):
                    # Preserve outputs that the backend returned from elsewhere.
                    return wheel
                cached_wheel = destination / wheel.name
                try:
                    return wheel.replace(cached_wheel)
                except PermissionError as e:
                    # Windows may block replacing a cached wheel being installed.
                    if (
                        getattr(e, "winerror", None) in (5, 32)
                        and destination == archive.parent
                        and is_zipfile(cached_wheel)
                    ):
                        return cached_wheel
                    raise

    def _should_prepare(self, archive: Path) -> bool:
        return archive.is_dir() or not self._is_wheel(archive)

    @classmethod
    def _is_wheel(cls, archive: Path) -> bool:
        return archive.suffix == ".whl"
