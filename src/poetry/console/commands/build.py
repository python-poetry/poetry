from __future__ import annotations

from pathlib import Path

from cleo.helpers import option

from poetry.console.commands.env_command import EnvCommand
from poetry.utils.env import build_environment


class BuildCommand(EnvCommand):
    name = "build"
    description = "Builds a package, as a tarball and a wheel by default."

    options = [
        option("format", "f", "Limit the format to either sdist or wheel.", flag=False),
        option(
            "output",
            "o",
            "Set output directory for build artifacts. Default is `dist`.",
            default="dist",
            flag=False,
        ),
    ]

    loggers = [
        "poetry.core.masonry.builders.builder",
        "poetry.core.masonry.builders.sdist",
        "poetry.core.masonry.builders.wheel",
    ]

    def _build(
        self,
        fmt: str,
        executable: str | Path | None = None,
        *,
        target_dir: Path | None = None,
    ) -> None:
        from poetry.masonry.builders import BUILD_FORMATS

        if fmt in BUILD_FORMATS:
            builders = [BUILD_FORMATS[fmt]]
        elif fmt == "all":
            builders = list(BUILD_FORMATS.values())
        else:
            raise ValueError(f"Invalid format: {fmt}")

        for builder in builders:
            builder(self.poetry, executable=executable).build(target_dir)

    def handle(self) -> int:
        if not self.poetry.is_package_mode:
            self.line_error("Building a package is not possible in non-package mode.")
            return 1

        with build_environment(poetry=self.poetry, env=self.env, io=self.io) as env:
            fmt = self.option("format") or "all"
            dist_dir = Path(self.option("output"))
            package = self.poetry.package
            self.line(
                f"Building <c1>{package.pretty_name}</c1> (<c2>{package.version}</c2>)"
            )

            if not dist_dir.is_absolute():
                dist_dir = self.poetry.pyproject_path.parent / dist_dir
            self._build(fmt, executable=env.python, target_dir=dist_dir)

        return 0
