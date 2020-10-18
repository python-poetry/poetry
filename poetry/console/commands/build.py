from cleo import option

from .env_command import EnvCommand


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

    def handle(self):
        from poetry.core.masonry import Builder

        fmt = "all"
        if self.option("format"):
            fmt = self.option("format")

        package = self.poetry.package
        self.line(
            "Building <c1>{}</c1> (<c2>{}</c2>)".format(
                package.pretty_name, package.version
            )
        )

        builder = Builder(self.poetry)
        builder.build(fmt, executable=self.env.python)
