from poetry.installation import Installer

from .command import Command


class RemoveCommand(Command):
    """
    Removes a package from the project dependencies.

    remove
        { packages* : Packages that should be removed. }
        {--D|dev : Removes a package from the development dependencies. }
        {--dry-run : Outputs the operations but will not execute anything
                     (implicitly enables --verbose). }
    """

    help = """The <info>remove</info> command removes a package from the current
list of installed packages

<info>poetry remove</info>"""

    def handle(self):
        packages = self.argument('packages')
        is_dev = self.option('dev')

        original_content = self.poetry.file.read()
        content = self.poetry.file.read()
        poetry_content = content['tool']['poetry']
        section = 'dependencies'
        if is_dev:
            section = 'dev-dependencies'

        # Deleting entries
        requirements = {}
        for name in packages:
            found = False
            for key in poetry_content[section]:
                if key.lower() == name.lower():
                    found = True
                    requirements[name] = poetry_content[section][name]
                    break

            if not found:
                raise ValueError(f'Package {name} not found')

        for key in requirements:
            del poetry_content[section][key]

        # Write the new content back
        self.poetry.file.write(content)

        # Update packages
        self.reset_poetry()

        installer = Installer(
            self.output,
            self.poetry.package,
            self.poetry.locker,
            self.poetry.pool
        )

        installer.dry_run(self.option('dry-run'))
        installer.update(True)
        installer.whitelist(requirements)

        try:
            status = installer.run()
        except Exception:
            self.poetry.file.write(original_content)

            raise

        if status != 0 or self.option('dry-run'):
            # Revert changes
            if not self.option('dry-run'):
                self.error(
                    '\n'
                    'Removal failed, reverting poetry.toml '
                    'to its original content.'
                )

            self.poetry.file.write(original_content)

        return status
