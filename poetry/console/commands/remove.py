import toml

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
        packages = [p.lower() for p in self.argument('packages')]
        is_dev = self.option('dev')

        with self.poetry.locker.original.path.open() as fd:
            content = fd.read().split('\n')

        # Trying to figure out where are our dependencies
        # If we find a toml library that keeps comments
        # We could remove this whole section
        section = '[dependencies]'
        if is_dev:
            section = '[dev-dependencies]'

        # Searching for package in
        in_section = False
        indices = []
        requirements = {}
        for i, line in enumerate(content):
            line = line.strip()

            if line == section:
                in_section = True
                continue

            if in_section:
                if not line:
                    # End of section
                    break

                requirement = toml.loads(line)
                name = list(requirement.keys())[0].lower()
                version = requirement[name]

                if name in packages:
                    requirements[name] = version
                    indices.append(i)
                    break

        if not indices or len(indices) != len(packages):
            raise RuntimeError(
                'Packages are not present in your poetry.toml file'
            )

        new_content = []
        for i, line in enumerate(content):
            if i in indices:
                continue

            new_content.append(line)

        new_content = '\n'.join(new_content)
        with self.poetry.locker.original.path.open('w') as fd:
            fd.write(new_content)

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
            with self.poetry.locker.original.path.open('w') as fd:
                fd.write('\n'.join(content))

            raise

        if status != 0 or self.option('dry-run'):
            # Revert changes
            if not self.option('dry-run'):
                self.error(
                    '\n'
                    'Removal failed, reverting poetry.toml '
                    'to its original content.'
                )

            with self.poetry.locker.original.path.open('w') as fd:
                fd.write('\n'.join(content))

        return status
