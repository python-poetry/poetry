import hashlib

import toml
import requests

from pathlib import Path

from poetry.locations import CONFIG_DIR
from poetry.semver.constraints import Constraint
from poetry.semver.constraints import MultiConstraint

from .builders.builder import Builder


class Publisher:

    def __init__(self, poetry, io):
        self._poetry = poetry
        self._package = poetry.package
        self._io = io

    def publish(self, repository_name):
        if repository_name:
            self._io.writeln(
                f'Publishing <info>{self._package.pretty_name}</info> '
                f'(<comment>{self._package.pretty_version}</comment>) '
                f'to <fg=cyan>{repository_name}</>'
            )
        else:
            self._io.writeln(
                f'Publishing <info>{self._package.pretty_name}</info> '
                f'(<comment>{self._package.pretty_version}</comment>) '
                f'to <fg=cyan>PyPI</>'
            )

        if not repository_name:
            url = 'https://upload.pypi.org/legacy/'
        else:
            # Retrieving config information
            config_file = Path(CONFIG_DIR) / 'config.toml'

            if not config_file.exists():
                raise RuntimeError(
                    'Config file does not exist. '
                    'Unable to get repository information'
                )

            with config_file.open() as f:
                config = toml.loads(f.read())

            if (
                'repositories' not in config
                or repository_name not in config['repositories']
            ):
                raise RuntimeError(
                    f'Repository {repository_name} is not defined'
                )

            url = config['repositories'][repository_name]['url']

        username = None
        password = None
        auth_file = Path(CONFIG_DIR) / 'auth.toml'
        if not auth_file.exists():
            # No auth file, we will ask for info later
            auth_config = {}
        else:
            with auth_file.open() as f:
                auth_config = toml.loads(f.read())

            if 'http-basic' in auth_config and repository_name in auth_config['http-basic']:
                config = auth_config['http-basic'][repository_name]

                username = config.get('username')
                password = config.get('password')

        return self.upload(url, username=username, password=password)

    def upload(self, url, username=None, password=None):
        data = self.build_post_data('file_upload')

    def upload_file(self, file, url, username, password):
        data = self.build_post_data('file_upload')

        data['protocol_version'] = '1'
        if file.suffix == '.whl':
            data['filetype'] = 'bdist_wheel'
            py2_support = self._package.python_constraint.matches(
                MultiConstraint([
                    Constraint('>=', '2.0.0'),
                    Constraint('<', '3.0.0')
                ])
            )
            data['pyversion'] = ('py2.' if py2_support else '') + 'py3'
        else:
            data['filetype'] = 'sdist'

        with file.open('rb') as f:
            content = f.read()
            files = {'content': (file.name, content)}
            data['md5_digest'] = hashlib.md5(content).hexdigest()

        log.info('Uploading %s...', file)
        resp = requests.post(repo['url'],
                             data=data,
                             files=files,
                             auth=(repo['username'], repo['password']),
                             )
        resp.raise_for_status()

    def build_post_data(self, action):
        builder = Builder(self._poetry, self._io)

        d = {
            ":action": action,

            "name": self._package.name,
            "version": self._package.version,

            # additional meta-data
            "metadata_version": '1.2',
            "summary": self._package.description,
            "home_page": self._package.homepage or self._package.repository_url,
            "author": self._package.author_name,
            "author_email": self._package.author_email,
            "maintainer": self._package.author_name,
            "maintainer_email": self._package.author_email,
            "license": self._package.license,
            "description": self._package.readme,
            "keywords": ','.join(self._package.keywords),
            "platform": None if self._package.platform == '*' else self._package.platform,
            "classifiers": builder.get_classifers(),
            "download_url": None,
            "supported_platform": None if self._package.platform == '*' else self._package.platform,
            "project_urls": [],
            "provides_dist": [],
            "obsoletes_dist": [],
            "requires_dist": [d.to_pep_508() for d in self._package.requires],
            "requires_external": [],
            "requires_python": builder.convert_python_version(),
        }

        return {k: v for k, v in d.items() if v}
