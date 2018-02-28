from pathlib import Path

from .packages import Locker
from .packages import Package
from .repositories.pypi_repository import PyPiRepository
from .semver.helpers import normalize_version
from .utils.toml_file import TomlFile


class Poetry:

    VERSION = '0.1.0'

    def __init__(self,
                 config: dict,
                 package: Package,
                 locker: Locker):
        self._package = package
        self._config = config
        self._locker = locker
        self._repository = PyPiRepository()

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
    def repository(self) -> PyPiRepository:
        return self._repository

    @classmethod
    def create(cls, cwd) -> 'Poetry':
        poetry_file = Path(cwd) / 'poetry.toml'

        if not poetry_file.exists():
            raise RuntimeError(
                f'Poetry could not find a poetry.json file in {cwd}'
            )

        # TODO: validate file content
        local_config = TomlFile(poetry_file.as_posix()).read()

        # Load package
        package_config = local_config['package']
        name = package_config['name']
        pretty_version = package_config['version']
        version = normalize_version(pretty_version)
        package = Package(name, version, pretty_version)

        if 'python_versions' in package_config:
            package.python_versions = package_config['python_versions']

        if 'platform' in package_config:
            package.platform = package_config['platform']

        if 'dependencies' in local_config:
            for name, constraint in local_config['dependencies'].items():
                package.add_dependency(name, constraint)

        if 'dev-dependencies' in local_config:
            for name, constraint in local_config['dev-dependencies'].items():
                package.add_dependency(name, constraint, category='dev')

        locker = Locker(poetry_file.with_suffix('.lock'), poetry_file)

        return cls(local_config, package, locker)
