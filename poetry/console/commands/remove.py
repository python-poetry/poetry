from cleo.helpers import argument
from cleo.helpers import option

from ...utils.helpers import canonicalize_name
from .installer_command import InstallerCommand


class RemoveCommand(InstallerCommand):

    name = "remove"
    description = "Removes a package from the project dependencies."

    arguments = [argument("packages", "The packages to remove.", multiple=True)]
    options = [
        option("dev", "D", "Remove a package from the development dependencies."),
        option(
            "dry-run",
            None,
            "Output the operations but do not execute anything "
            "(implicitly enables --verbose).",
        ),
    ]

    help = """The <info>remove</info> command removes a package from the current
list of installed packages

<info>poetry remove</info>"""

    loggers = ["poetry.repositories.pypi_repository", "poetry.inspection.info"]

    def handle(self) -> int:
        packages = self.argument("packages")
        is_dev = self.option("dev")

        content = self.poetry.file.read()
        poetry_content = content["tool"]["poetry"]
        section = "dependencies"
        if is_dev:
            section = "dev-dependencies"

        # Deleting entries
        requirements = {}
        for name in packages:
            found = False
            for key in poetry_content[section]:
                if key.lower() == name.lower():
                    found = True
                    requirements[key] = poetry_content[section][key]
                    break

            if not found:
                raise ValueError("Package {} not found".format(name))

        for key in requirements:
            del poetry_content[section][key]

            dependencies = (
                self.poetry.package.requires
                if section == "dependencies"
                else self.poetry.package.dev_requires
            )

            for i, dependency in enumerate(reversed(dependencies)):
                if dependency.name == canonicalize_name(key):
                    del dependencies[-i]

        # Update packages
        self._installer.use_executor(
            self.poetry.config.get("experimental.new-installer", False)
        )

        self._installer.dry_run(self.option("dry-run"))
        self._installer.verbose(self._io.is_verbose())
        self._installer.update(True)
        self._installer.whitelist(requirements)

        status = self._installer.run()

        if not self.option("dry-run") and status == 0:
            self.poetry.file.write(content)

        return status
