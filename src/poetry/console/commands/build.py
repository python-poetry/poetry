from cleo.helpers import option

from poetry.console.commands.env_command import EnvCommand


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

    def handle(self) -> None:
        from poetry.core.masonry.builder import Builder

        fmt = "all"
        if self.option("format"):
            fmt = self.option("format")

        package = self.poetry.package
        self.line(
            f"Building <c1>{package.pretty_name}</c1> (<c2>{package.version}</c2>)"
        )

        builder = Builder(self.poetry)
        builder.build(fmt, executable=self.env.python)
