from .venv_command import VenvCommand


class BuildCommand(VenvCommand):
    """
    Builds a package, as a tarball and a wheel by default.

    build
        { --f|format= : Limit the format to either wheel or sdist. }
    """

    def handle(self):
        from poetry.masonry import Builder

        fmt = "all"
        if self.option("format"):
            fmt = self.option("format")

        package = self.poetry.package
        self.line(
            "Building <info>{}</> (<comment>{}</>)".format(
                package.pretty_name, package.version
            )
        )

        builder = Builder(self.poetry, self.venv, self.output)
        builder.build(fmt)
