from cleo import option

from poetry.console.commands.installer_command import InstallerCommand


class BuildCommand(InstallerCommand):

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

        executable = None
        if self.poetry.package.build_requires:
            # ensure build requirements are available if specified
            self.installer.categories({"build"}).run()
            executable = self.installer.env.python

        builder.build(fmt, executable=executable)
