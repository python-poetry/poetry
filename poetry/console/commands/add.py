import re

from typing import List
from typing import Tuple

from poetry.installation import Installer
from poetry.semver.version_parser import VersionParser
from poetry.version.version_selector import VersionSelector

from .command import Command


class AddCommand(Command):
    """
    Add a new depdency to <comment>poetry.toml</>.

    add
        { name* : Packages to add. }
        {--D|dev : Add package as development dependency. }
        {--optional : Add as an optional dependency. }
    """

    help = """The add command adds required packages to your <comment>poetry.toml</> and installs them.

If you do not specify a version constraint, poetry will choose a suitable one based on the available package versions.
"""

    def handle(self):
        names = self.argument('name')
        is_dev = self.option('dev')

        requirements = self._determine_requirements(names)
        requirements = self._format_requirements(requirements)

        # validate requirements format
        parser = VersionParser()
        for constraint in requirements.values():
            parser.parse_constraints(constraint)

        # Trying to figure out where to add our dependencies
        # If we find a toml library that keeps comments
        # We could remove this whole section
        section = '[dependencies]'
        if is_dev:
            section = '[dev-dependencies]'

        new_content = None
        with self.poetry.locker.original.path.open() as fd:
            content = fd.read().split('\n')

        in_section = False
        index = None
        for i, line in enumerate(content):
            line = line.strip()

            if line == section:
                in_section = True
                continue

            if in_section and not line:
                index = i
                break

        if index is not None:
            for i, require in enumerate(requirements.items()):
                name, version = require
                content.insert(
                    index + i,
                    f'{name} = "{version}"'
                )

            new_content = '\n'.join(content)

        if new_content is not None:
            with self.poetry.locker.original.path.open('w') as fd:
                fd.write(new_content)
        else:
            # We could not find where to put the dependencies
            # We raise an warning
            self.warning('Unable to automatically add dependencies')
            self.warning('Add them manually to your poetry.toml')

            return 1

        # Cosmetic new line
        self.line('')

        # Update packages
        self.reset_poetry()

        installer = Installer(
            self.output,
            self.poetry.package,
            self.poetry.locker,
            self.poetry.repository
        )

        installer.update(True)
        installer.whitelist(requirements)

        installer.run()

    def _determine_requirements(self, requires: List[str]) -> List[str]:
        if not requires:
            return []

        requires = self._parse_name_version_pairs(requires)
        result = []
        for requirement in requires:
            if 'version' not in requirement:
                # determine the best version automatically
                name, version = self._find_best_version_for_package(
                    requirement['name']
                )
                requirement['version'] = version
                requirement['name'] = name

                self.line(
                    f'Using version <info>{version}</> for <info>{name}</>'
                )
            else:
                # check that the specified version/constraint exists
                # before we proceed
                name, _ = self._find_best_version_for_package(
                    requirement['name'], requirement['version']
                )

                requirement['name'] = name

            result.append(f'{requirement["name"]} {requirement["version"]}')

        return result

    def _find_best_version_for_package(self,
                                       name,
                                       required_version=None
                                       ) -> Tuple[str, str]:
        selector = VersionSelector(self.poetry.repository)
        package = selector.find_best_candidate(name, required_version)

        if not package:
            # TODO: find similar
            raise ValueError(
                f'Could not find a matching version of package {name}'
            )

        return (
            package.pretty_name,
            selector.find_recommended_require_version(package)
        )

    def _parse_name_version_pairs(self, pairs: list) -> list:
        result = []

        for i in range(len(pairs)):
            pair = re.sub('^([^=: ]+)[=: ](.*)$', '\\1 \\2', pairs[i].strip())
            pair = pair.strip()

            if ' ' in pair:
                name, version = pair.split(' ', 2)
                result.append({
                    'name': name,
                    'version': version
                })
            else:
                result.append({
                    'name': pair
                })

        return result

    def _format_requirements(self, requirements: List[str]) -> dict:
        requires = {}
        requirements = self._parse_name_version_pairs(requirements)
        for requirement in requirements:
            requires[requirement['name']] = requirement['version']

        return requires
