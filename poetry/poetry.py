from pathlib import Path

from .__version__ import __version__
from .packages import Locker
from .packages import Package
from .repositories import Pool
from .repositories.pypi_repository import PyPiRepository
from .semver.helpers import normalize_version
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

        # TODO: validate file content
        local_config = TomlFile(poetry_file.as_posix()).read(True)
        if 'tool' not in local_config or 'poetry' not in local_config['tool']:
            raise RuntimeError(
                f'[tool.poetry] section not found in {poetry_file.name}'
            )
        local_config = local_config['tool']['poetry']

        # Load package
        name = local_config['name']
        pretty_version = local_config['version']
        version = normalize_version(pretty_version)
        package = Package(name, version, pretty_version)

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

        locker = Locker(poetry_file.with_suffix('.lock'), local_config)

        return cls(poetry_file, local_config, package, locker)
