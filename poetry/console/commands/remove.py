from cleo import argument
from cleo import option

from .env_command import EnvCommand


class RemoveCommand(EnvCommand):

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

    loggers = ["poetry.repositories.pypi_repository"]

    def handle(self):
        from poetry.installation.installer import Installer

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

        installer = Installer(
            self.io, self.env, self.poetry.package, self.poetry.locker, self.poetry.pool
        )

        installer.dry_run(self.option("dry-run"))
        installer.update(True)
        installer.whitelist(requirements)

        try:
            status = installer.run()
        except Exception:
            self.poetry.file.write(original_content)

            raise

        if status != 0 or self.option("dry-run"):
            # Revert changes
            if not self.option("dry-run"):
                self.error(
                    "\n"
                    "Removal failed, reverting pyproject.toml "
                    "to its original content."
                )

            self.poetry.file.write(original_content)

        return status
