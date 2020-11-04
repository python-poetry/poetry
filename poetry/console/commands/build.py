from cleo import option

from .env_command import EnvCommand


class BuildCommand(EnvCommand):

    name = "build"
    description = "Builds a package, as a tarball and a wheel by default."

    options = [
        option("format", "f", "Limit the format to either sdist or wheel.", flag=False),
        option(
            "lock",
            "l",
            "Add all dependencies as locked dependencies in the distributed pyproject.toml",
            flag=True,
        ),
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

        lock = self.option("lock")

        package = self.poetry.package
        self.line(
            "Building <c1>{}</c1> (<c2>{}</c2>)".format(
                package.pretty_name, package.version
            )
        )

        original_content = self.poetry.file.read()
        if lock:
            section = "dependencies"

            content = self.poetry.file.read()
            poetry_content = content["tool"]["poetry"]
            if section not in poetry_content:
                poetry_content[section] = {}

            for dependency_package in self._poetry.locker.lock_data["package"]:
                name = dependency_package["name"]
                version = dependency_package["version"]
                poetry_content[section][name] = version

            self.poetry.file.write(content)

        builder = Builder(self.poetry)
        builder.build(fmt, executable=self.env.python)

        if lock:
            self.poetry.file.write(original_content)
