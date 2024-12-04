from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import ClassVar

from cleo.helpers import option

from poetry.console.commands.env_command import EnvCommand
from poetry.utils.env import build_environment
from poetry.utils.helpers import remove_directory


if TYPE_CHECKING:
    from cleo.io.inputs.option import Option
    from cleo.io.io import IO

    from poetry.poetry import Poetry
    from poetry.utils.env import Env


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

    def handle(self) -> int:
        return self.build(
            self.poetry,
            self.env,
            self.io,
            self.option("format"),
            self.option("clean"),
            self.option("local-version"),
            self.option("output"),
        )

    @staticmethod
    def build(
        poetry: Poetry,
        env: Env,
        io: IO,
        format: str = "all",
        clean: bool = True,
        local_version_label: str | None = None,
        output: str = "dist",
    ) -> int:
        from poetry.masonry.builders import BUILD_FORMATS

        if not poetry.is_package_mode:
            io.write_error_line(
                "Building a package is not possible in non-package mode."
            )
            return 1

        with build_environment(poetry=poetry, env=env, io=io) as env:
            dist_dir = Path(output)
            package = poetry.package
            io.write_line(
                f"Building <c1>{package.pretty_name}</c1> (<c2>{package.version}</c2>)"
            )

            if not dist_dir.is_absolute():
                dist_dir = poetry.pyproject_path.parent / dist_dir

            if clean:
                remove_directory(path=dist_dir, force=True)

            if format in BUILD_FORMATS:
                builders = [BUILD_FORMATS[format]]
            elif format == "all":
                builders = list(BUILD_FORMATS.values())
            else:
                raise ValueError(f"Invalid build format: {format}")

            if local_version_label:
                poetry.package.version = poetry.package.version.replace(
                    local=local_version_label
                )

            for builder in builders:
                builder(poetry, executable=env.python).build(dist_dir)

        return 0
