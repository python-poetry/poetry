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
        {--dry-run : Outputs the operations but will not execute anything
                     (implicitly enables --verbose). }
    """

    help = """The add command adds required packages to your <comment>poetry.toml</> and installs them.

If you do not specify a version constraint, poetry will choose a suitable one based on the available package versions.
"""

    def handle(self):
        packages = self.argument('name')
        is_dev = self.option('dev')

        section = 'dependencies'
        if is_dev:
            section = 'dev-dependencies'

        original_content = self.poetry.file.read()
        content = self.poetry.file.read()
        poetry_content = content['tool']['poetry']

        for name in packages:
            for key in poetry_content[section]:
                if key.lower() == name.lower():
                    raise ValueError(f'Package {name} is already present')

        requirements = self._determine_requirements(packages)
        requirements = self._format_requirements(requirements)

        # validate requirements format
        parser = VersionParser()
        for constraint in requirements.values():
            parser.parse_constraints(constraint)

        for name, constraint in requirements.items():
            poetry_content[section][name] = constraint

        # Write new content
        self.poetry.file.write(content)

        # Cosmetic new line
        self.line('')

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
                    'Addition failed, reverting poetry.toml '
                    'to its original content.'
                )

            self.poetry.file.write(original_content)

        return status

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
        selector = VersionSelector(self.poetry.pool)
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
