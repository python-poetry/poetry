from __future__ import annotations

from cleo.helpers import option

from poetry.console.commands.env_command import EnvCommand
from poetry.utils.env import build_environment


class BuildCommand(EnvCommand):
    name = "build"
    description = "Builds a package, as a tarball and a wheel by default."

    options = [
        option("format", "f", "Limit the format to either sdist or wheel.", flag=False)
    ]

    loggers = [
        "poetry.core.masonry.builders.builder",
        "poetry.core.masonry.builders.sdist",
        "poetry.core.masonry.builders.wheel",
    ]

    def handle(self) -> int:
        from poetry.core.masonry.builder import Builder

        with build_environment(poetry=self.poetry, env=self.env, io=self.io) as env:
            fmt = self.option("format") or "all"
            package = self.poetry.package
            self.line(
                f"Building <c1>{package.pretty_name}</c1> (<c2>{package.version}</c2>)"
            )

            builder = Builder(self.poetry)
            builder.build(fmt, executable=env.python)

        return 0
