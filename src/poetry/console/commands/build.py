from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

from cleo.helpers import option
from poetry.core.constraints.version import Version

from poetry.console.commands.env_command import EnvCommand
from poetry.masonry.builders import BUILD_FORMATS
from poetry.utils._compat import metadata
from poetry.utils.helpers import remove_directory
from poetry.utils.isolated_build import isolated_builder


if TYPE_CHECKING:
    from collections.abc import Callable

    from build import DistributionType
    from cleo.io.inputs.option import Option


class BuildCommand(EnvCommand):
    name = "build"
    description = "Builds a package, as a tarball and a wheel by default."

    options: ClassVar[list[Option]] = [
        option("format", "f", "Limit the format to either sdist or wheel.", flag=False),
        option(
            "clean",
            description="Clean output directory before building.",
            flag=True,
        ),
        option(
            "local-version",
            "l",
            "Add or replace a local version label to the build.",
            flag=False,
        ),
        option(
            "output",
            "o",
            "Set output directory for build artifacts. Default is `dist`.",
            default="dist",
            flag=False,
        ),
    ]

    loggers: ClassVar[list[str]] = [
        "poetry.core.masonry.builders.builder",
        "poetry.core.masonry.builders.sdist",
        "poetry.core.masonry.builders.wheel",
    ]

    def _requested_formats(self) -> list[DistributionType]:
        fmt = self.option("format") or "all"
        formats: list[DistributionType]

        if fmt in BUILD_FORMATS:
            formats = [fmt]  # type: ignore[list-item]
        elif fmt == "all":
            formats = list(BUILD_FORMATS.keys())  # type: ignore[arg-type]
        else:
            raise ValueError(f"Invalid format: {fmt}")

        return formats

    def _config_settings(self) -> dict[str, str]:
        config_settings = {}

        if local_version_label := self.option("local-version"):
            config_settings["local-version"] = local_version_label

        return config_settings

    def _build(
        self,
        fmt: DistributionType,
        executable: Path,
        target_dir: Path,
        config_settings: dict[str, Any],
    ) -> None:
        if fmt not in BUILD_FORMATS:
            raise ValueError(f"Invalid format: {fmt}")

        builder = BUILD_FORMATS[fmt]

        builder(
            self.poetry,
            executable=executable,
            config_settings=config_settings,
        ).build(target_dir)

    def _isolated_build(
        self,
        fmt: DistributionType,
        executable: Path,
        target_dir: Path,
        config_settings: dict[str, Any],
    ) -> None:
        if fmt not in BUILD_FORMATS:
            raise ValueError(f"Invalid format: {fmt}")

        with isolated_builder(
            source=self.poetry.file.path.parent,
            distribution=fmt,
            python_executable=executable,
        ) as builder:
            builder.build(fmt, target_dir, config_settings=config_settings)

    def _requires_isolated_build(self) -> bool:
        """
        Determines if an isolated build is required.

        An isolated build is required if:
        - The package has a build script.
        - There are multiple build system dependencies.
        - The build dependency is not `poetry-core`.
        - The installed `poetry-core` version does not satisfy the build dependency constraints.
        - The build dependency has a source type (e.g. is a VcsDependency).

        :returns: True if an isolated build is required, False otherwise.
        """
        if (
            self.poetry.package.build_script
            or len(self.poetry.build_system_dependencies) != 1
        ):
            return True

        build_dependency = self.poetry.build_system_dependencies[0]
        if build_dependency.name != "poetry-core":
            return True

        poetry_core_version = Version.parse(metadata.version("poetry-core"))

        return bool(
            not build_dependency.constraint.allows(poetry_core_version)
            or build_dependency.source_type
        )

    def _get_builder(self) -> Callable[..., None]:
        if self._requires_isolated_build():
            return self._isolated_build

        return self._build

    def handle(self) -> int:
        if not self.poetry.is_package_mode:
            self.line_error("Building a package is not possible in non-package mode.")
            return 1

        dist_dir = Path(self.option("output"))
        package = self.poetry.package
        self.line(
            f"Building <c1>{package.pretty_name}</c1> (<c2>{package.version}</c2>)"
        )

        if not dist_dir.is_absolute():
            dist_dir = self.poetry.pyproject_path.parent / dist_dir

        if self.option("clean"):
            remove_directory(path=dist_dir, force=True)

        build = self._get_builder()

        for fmt in self._requested_formats():
            self.line(f"Building <info>{fmt}</info>")
            build(
                fmt,
                executable=self.env.python,
                target_dir=dist_dir,
                config_settings=self._config_settings(),
            )

        return 0
