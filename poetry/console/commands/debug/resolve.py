import re

from typing import List

from poetry.packages import Dependency
from poetry.puzzle import Solver
from poetry.repositories.repository import Repository
from poetry.semver.version_parser import VersionParser

from ..command import Command


class DebugResolveCommand(Command):
    """
    Debugs dependency resolution.

    debug:resolve
        { package?* : packages to resolve. }
    """

    def handle(self):
        packages = self.argument('package')

        if not packages:
            package = self.poetry.package
            dependencies = package.requires + package.dev_requires
        else:
            requirements = self._determine_requirements(packages)
            requirements = self._format_requirements(requirements)

            # validate requirements format
            parser = VersionParser()
            for constraint in requirements.values():
                parser.parse_constraints(constraint)

            dependencies = []
            for name, constraint in requirements.items():
                dependencies.append(
                    Dependency(name, constraint)
                )

        solver = Solver(
            self.poetry.package,
            self.poetry.pool,
            Repository(),
            self.output
        )

        ops = solver.solve(dependencies)

        self.line('')
        self.line('Resolution results:')
        self.line('')

        for op in ops:
            package = op.package
            self.line(f'  - <info>{package.name}</info> '
                      f'(<comment>{package.version}</comment>)')

    def _determine_requirements(self, requires: List[str]) -> List[str]:
        if not requires:
            return []

        requires = self._parse_name_version_pairs(requires)
        result = []
        for requirement in requires:
            if 'version' not in requirement:
                requirement['version'] = '*'

            result.append(f'{requirement["name"]} {requirement["version"]}')

        return result

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
