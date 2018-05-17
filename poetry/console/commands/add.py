import re

from typing import List
from typing import Tuple

from .venv_command import VenvCommand


class AddCommand(VenvCommand):
    """
    Add a new dependency to <comment>pyproject.toml</>.

    add
        { name* : Packages to add. }
        { --D|dev : Add package as development dependency. }
        { --git= : The url of the Git repository. }
        { --path= : The path to a dependency. }
        { --E|extras=* : Extras to activate for the dependency. }
        { --optional : Add as an optional dependency. }
        { --allow-prereleases : Accept prereleases. }
        { --dry-run : Outputs the operations but will not execute anything
                     (implicitly enables --verbose). }
    """

    help = """The add command adds required packages to your <comment>pyproject.toml</> and installs them.

If you do not specify a version constraint, poetry will choose a suitable one based on the available package versions.
"""

    _loggers = [
        'poetry.repositories.pypi_repository'
    ]

    def handle(self):
        from poetry.installation import Installer
        from poetry.semver import parse_constraint

        packages = self.argument('name')
        is_dev = self.option('dev')

        if (self.option('git') or self.option('path') or self.option('extras')) and len(packages) > 1:
            raise ValueError(
                'You can only specify one package '
                'when using the --git or --path options'
            )

        if self.option('git') and self.option('path'):
            raise RuntimeError(
                '--git and --path cannot be used at the same time'
            )

        section = 'dependencies'
        if is_dev:
            section = 'dev-dependencies'

        original_content = self.poetry.file.read()
        content = self.poetry.file.read()
        poetry_content = content['tool']['poetry']

        for name in packages:
            for key in poetry_content[section]:
                if key.lower() == name.lower():
                    raise ValueError(
                        'Package {} is already present'.format(name)
                    )

        if self.option('git') or self.option('path'):
            requirements = {
                packages[0]: ''
            }
        else:
            requirements = self._determine_requirements(
                packages,
                allow_prereleases=self.option('allow-prereleases')
            )
            requirements = self._format_requirements(requirements)

            # validate requirements format
            for constraint in requirements.values():
                parse_constraint(constraint)

        for name, constraint in requirements.items():
            constraint = {
                'version': constraint
            }

            if self.option('git'):
                del constraint['version']

                constraint['git'] = self.option('git')
            elif self.option('path'):
                del constraint['version']

                constraint['path'] = self.option('path')

            if self.option('optional'):
                constraint['optional'] = True

            if self.option('allow-prereleases'):
                constraint['allows-prereleases'] = True

            if self.option('extras'):
                constraint['extras'] = self.option('extras')

            if len(constraint) == 1 and 'version' in constraint:
                constraint = constraint['version']

            poetry_content[section][name] = constraint

        # Write new content
        self.poetry.file.write(content)

        # Cosmetic new line
        self.line('')

        # Update packages
        self.reset_poetry()

        installer = Installer(
            self.output,
            self.venv,
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
                    'Addition failed, reverting pyproject.toml '
                    'to its original content.'
                )

            self.poetry.file.write(original_content)

        return status

    def _determine_requirements(self,
                                requires,  # type: List[str]
                                allow_prereleases=False,  # type: bool
                                ):  # type: (...) -> List[str]
        if not requires:
            return []

        requires = self._parse_name_version_pairs(requires)
        result = []
        for requirement in requires:
            if 'version' not in requirement:
                # determine the best version automatically
                name, version = self._find_best_version_for_package(
                    requirement['name'],
                    allow_prereleases=allow_prereleases
                )
                requirement['version'] = version
                requirement['name'] = name

                self.line(
                    'Using version <info>{}</> for <info>{}</>'
                    .format(version, name)
                )
            else:
                # check that the specified version/constraint exists
                # before we proceed
                name, _ = self._find_best_version_for_package(
                    requirement['name'], requirement['version'],
                    allow_prereleases=allow_prereleases
                )

                requirement['name'] = name

            result.append(
                '{} {}'.format(requirement['name'], requirement['version'])
            )

        return result

    def _find_best_version_for_package(self,
                                       name,
                                       required_version=None,
                                       allow_prereleases=False
                                       ):  # type: (...) -> Tuple[str, str]
        from poetry.version.version_selector import VersionSelector

        selector = VersionSelector(self.poetry.pool)
        package = selector.find_best_candidate(
            name, required_version,
            allow_prereleases=allow_prereleases
        )

        if not package:
            # TODO: find similar
            raise ValueError(
                'Could not find a matching version of package {}'.format(name)
            )

        return (
            package.pretty_name,
            selector.find_recommended_require_version(package)
        )

    def _parse_name_version_pairs(self, pairs):  # type: (list) -> list
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

    def _format_requirements(self, requirements):  # type: (List[str]) -> dict
        requires = {}
        requirements = self._parse_name_version_pairs(requirements)
        for requirement in requirements:
            requires[requirement['name']] = requirement['version']

        return requires
