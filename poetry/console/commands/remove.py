from cleo import argument
from cleo import option

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

    def handle(self):
        packages = self.argument("packages")
        is_dev = self.option("dev")

        original_content = self.poetry.file.read()
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

        # Write the new content back
        self.poetry.file.write(content)

        # Update packages
        self.reset_poetry()

        self._installer.use_executor(
            self.poetry.config.get("experimental.new-installer", False)
        )

        self._installer.dry_run(self.option("dry-run"))
        self._installer.verbose(self._io.is_verbose())
        self._installer.update(True)
        self._installer.whitelist(requirements)

        try:
            status = self._installer.run()
        except Exception:
            self.poetry.file.write(original_content)

            raise

        if status != 0 or self.option("dry-run"):
            # Revert changes
            if not self.option("dry-run"):
                self.line_error(
                    "\n"
                    "Removal failed, reverting pyproject.toml "
                    "to its original content."
                )

            self.poetry.file.write(original_content)

        return status
