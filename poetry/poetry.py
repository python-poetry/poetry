import json

from pathlib import Path

import jsonschema

from .__version__ import __version__
from .exceptions import InvalidProjectFile
from .packages import Dependency
from .packages import Locker
from .packages import Package
from .repositories import Pool
from .repositories.pypi_repository import PyPiRepository
from .utils.toml_file import TomlFile


class Poetry:

    VERSION = __version__

    def __init__(self,
                 file: Path,
                 config: dict,
                 package: Package,
                 locker: Locker):
        self._file = TomlFile(file)
        self._package = package
        self._config = config
        self._locker = locker

        # Configure sources
        self._pool = Pool()
        for source in self._config.get('source', []):
            self._pool.configure(source)

        # Always put PyPI last to prefere private repositories
        self._pool.add_repository(PyPiRepository())
        
    @property
    def file(self):
        return self._file

    @property
    def package(self) -> Package:
        return self._package

    @property
    def config(self) -> dict:
        return self._config

    @property
    def locker(self) -> Locker:
        return self._locker

    @property
    def pool(self) -> Pool:
        return self._pool

    @classmethod
    def create(cls, cwd) -> 'Poetry':
        poetry_file = Path(cwd) / 'pyproject.toml'

        if not poetry_file.exists():
            raise RuntimeError(
                f'Poetry could not find a pyproject.toml file in {cwd}'
            )

        local_config = TomlFile(poetry_file.as_posix()).read(True)
        if 'tool' not in local_config or 'poetry' not in local_config['tool']:
            raise RuntimeError(
                f'[tool.poetry] section not found in {poetry_file.name}'
            )
        local_config = local_config['tool']['poetry']

        # Checking validity
        cls.check(local_config)

        # Load package
        name = local_config['name']
        version = local_config['version']
        package = Package(name, version, version)

        for author in local_config['authors']:
            package.authors.append(author)

        package.description = local_config.get('description', '')
        package.homepage = local_config.get('homepage')
        package.repository_url = local_config.get('repository')
        package.license = local_config.get('license')
        package.keywords = local_config.get('keywords', [])

        if 'readme' in local_config:
            package.readme = Path(cwd) / local_config['readme']

        if 'platform' in local_config:
            package.platform = local_config['platform']

        if 'dependencies' in local_config:
            for name, constraint in local_config['dependencies'].items():
                if name.lower() == 'python':
                    package.python_versions = constraint
                    continue

                package.add_dependency(name, constraint)

        if 'dev-dependencies' in local_config:
            for name, constraint in local_config['dev-dependencies'].items():
                package.add_dependency(name, constraint, category='dev')

        if 'extras' in local_config:
            for extra_name, requirements in local_config['extras'].items():
                package.extras[extra_name] = [
                    Dependency(req, '*') for req in requirements
                ]

        if 'build' in local_config:
            package.build = local_config['build']

        if 'include' in local_config:
            package.include = local_config['include']

        if 'exclude' in local_config:
            package.exclude = local_config['exclude']

        locker = Locker(poetry_file.with_suffix('.lock'), local_config)

        return cls(poetry_file, local_config, package, locker)

    @classmethod
    def check(cls, config: dict, strict: bool = False):
        """
        Checks the validity of a configuration
        """
        schema = (
            Path(__file__).parent
            / 'json' / 'schemas' / 'poetry-schema.json'
        )

        schema = json.loads(schema.read_text())

        try:
            jsonschema.validate(
                config,
                schema
            )
        except jsonschema.ValidationError as e:
            message = e.message
            if e.path:
                message = f"[{'.'.join(e.path)}] {message}"

            raise InvalidProjectFile(message)

        return True
