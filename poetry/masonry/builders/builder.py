import os
import re

from collections import defaultdict
from pathlib import Path

from poetry.semver.constraints import Constraint
from poetry.semver.constraints import MultiConstraint
from poetry.semver.version_parser import VersionParser
from poetry.vcs import get_vcs

from ..metadata import Metadata
from ..utils.module import Module


AUTHOR_REGEX = re.compile('(?u)^(?P<name>[- .,\w\d\'’"()]+) <(?P<email>.+?)>$')


class Builder:

    AVAILABLE_PYTHONS = {
        '2',
        '2.7',
        '3',
        '3.4', '3.5', '3.6', '3.7'
    }

    def __init__(self, poetry, venv, io):
        self._poetry = poetry
        self._venv = venv
        self._io = io
        self._package = poetry.package
        self._path = poetry.file.parent
        self._module = Module(
            self._package.name, self._path.as_posix()
        )
        self._meta = Metadata.from_package(self._package)

    def build(self):
        raise NotImplementedError()

    def find_excluded_files(self) -> list:
        # Checking VCS
        vcs = get_vcs(self._path)
        if not vcs:
            return []

        ignored = vcs.get_ignored_files()
        result = []
        for file in ignored:
            try:
                file = Path(file).absolute().relative_to(self._path)
            except ValueError:
                # Should only happen in tests
                continue

            result.append(file)

        return result

    def find_files_to_add(self, exclude_build=True) -> list:
        """
        Finds all files to add to the tarball

        TODO: Support explicit include/exclude
        """
        excluded = self.find_excluded_files()
        src = self._module.path
        to_add = []

        for root, dirs, files in os.walk(src.as_posix()):
            root = Path(root)
            if root.name == '__pycache__':
                continue

            for file in files:
                file = root / file
                file = file.relative_to(self._path)

                if file in excluded:
                    continue

                if file.suffix == '.pyc':
                    continue

                self._io.writeln(
                    f' - Adding: <comment>{str(file)}</comment>',
                    verbosity=self._io.VERBOSITY_VERY_VERBOSE
                )
                to_add.append(file)

        # Include project files
        self._io.writeln(
            f' - Adding: <comment>pyproject.toml</comment>',
            verbosity=self._io.VERBOSITY_VERY_VERBOSE
        )
        to_add.append(Path('pyproject.toml'))

        # If a README is specificed we need to include it
        # to avoid errors
        if 'readme' in self._poetry.config:
            readme = self._path / self._poetry.config['readme']
            if readme.exists():
                self._io.writeln(
                    f' - Adding: <comment>{readme.relative_to(self._path)}</comment>',
                    verbosity=self._io.VERBOSITY_VERY_VERBOSE
                )
                to_add.append(readme.relative_to(self._path))

        # If a build script is specified and explicitely required
        # we add it to the list of files
        if self._package.build and not exclude_build:
            to_add.append(Path(self._package.build))

        return sorted(to_add)

    def convert_entry_points(self) -> dict:
        result = defaultdict(list)

        # Scripts -> Entry points
        for name, ep in self._poetry.config.get('scripts', {}).items():
            result['console_scripts'].append(f'{name} = {ep}')

        # Plugins -> entry points
        for groupname, group in self._poetry.config.get('plugins', {}).items():
            for name, ep in sorted(group.items()):
                result[groupname].append(f'{name} = {ep}')

        return dict(result)

    @classmethod
    def convert_author(cls, author) -> dict:
        m = AUTHOR_REGEX.match(author)

        name = m.group('name')
        email = m.group('email')

        return {
            'name': name,
            'email': email
        }

    def get_classifers(self):
        classifiers = []

        # Automatically set python classifiers
        parser = VersionParser()
        if self._package.python_versions == '*':
            python_constraint = parser.parse_constraints('~2.7 || ^3.4')
        else:
            python_constraint = self._package.python_constraint

        for version in sorted(self.AVAILABLE_PYTHONS):
            if python_constraint.matches(Constraint('=', version)):
                classifiers.append(f'Programming Language :: Python :: {version}')

        return classifiers

    def convert_python_version(self):
        constraint = self._package.python_constraint
        if isinstance(constraint, MultiConstraint):
            python_requires = ','.join(
                [str(c).replace(' ', '') for c in constraint.constraints]
            )
        else:
            python_requires = str(constraint).replace(' ', '')

        return python_requires
