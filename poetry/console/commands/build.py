from cleo import option

from .env_command import EnvCommand


class BuildCommand(EnvCommand):

    name = "build"
    description = "Builds a package, as a tarball and a wheel by default."

    options = [
        option("format", "f", "Limit the format to either sdist or wheel.", flag=False)
    ]

    def handle(self):
        from poetry.masonry import Builder

        fmt = "all"
        if self.option("format"):
            fmt = self.option("format")

        package = self.poetry.package
        self.line(
            "Building <c1>{}</c1> (<b>{}</b>)".format(
                package.pretty_name, package.version
            )
        )

        builder = Builder(self.poetry, self.env, self.io)
        builder.build(fmt)
