# -*- coding: utf-8 -*-

import re

import toml

from poetry.vcs.git import Git

_canonicalize_regex = re.compile(r"[-_.]+")


TESTS_DEFAULT = """from {package_name} import __version__


def test_version():
    assert '{version}' == __version__
"""


class Layout(object):

    def __init__(self, project, version='0.1.0', readme_format='md', author=None):
        self._project = project
        self._package_name = self._canonicalize_name(project).replace('-', '_')
        self._version = version
        self._readme_format = readme_format
        self._dependencies = {}
        self._dev_dependencies = {}
        self._include = []

        self._git = Git()
        git_config = self._git.config
        if not author:
            if (
                git_config.get('user.name')
                and git_config.get('user.email')
            ):
                author = '{} <{}>'.format(
                    git_config['user.name'],
                    git_config['user.email']
                )
            else:
                author = 'Your Name <you@example.com>'

        self._author = author

    def create(self, path, with_tests=True):
        self._dependencies = {}
        self._dev_dependencies = {}
        self._include = []

        path.mkdir(parents=True, exist_ok=True)

        self._create_default(path)
        self._create_readme(path)

        if with_tests:
            self._create_tests(path)

        self._write_poetry(path)

    def _create_default(self, path, src=True):
        raise NotImplementedError()

    def _create_readme(self, path):
        if self._readme_format == 'rst':
            readme_file = path / 'README.rst'
        else:
            readme_file = path / 'README.md'

        readme_file.touch()

    def _create_tests(self, path):
        self._dev_dependencies['pytest'] = '^3.0'

        tests = path / 'tests'
        tests_init = tests / '__init__.py'
        tests_default = tests / 'test_{}.py'.format(self._package_name)

        tests.mkdir()
        tests_init.touch(exist_ok=False)

        with tests_default.open('w') as f:
            f.write(
                TESTS_DEFAULT.format(
                    package_name=self._package_name,
                    version=self._version
                )
            )

    def _write_poetry(self, path):
        output = {
            'tool': {
                'poetry': {
                    'name': self._project,
                    'version': self._version,
                    'authors': [self._author],
                }
            }
        }

        content = toml.dumps(output, preserve=True)

        output = {
            'tool': {
                'poetry': {
                    'dependencies': {},
                    'dev-dependencies': {
                        'pytest': '^3.4'
                    }
                }
            }
        }

        content += '\n' + toml.dumps(output, preserve=True)

        poetry = path / 'pyproject.toml'

        with poetry.open('w') as f:
            f.write(content)

    def _canonicalize_name(self, name: str) -> str:
        return _canonicalize_regex.sub("-", name).lower()
