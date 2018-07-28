from __future__ import absolute_import
from __future__ import unicode_literals

import json

from .__version__ import __version__
from .config import Config
from .exceptions import InvalidProjectFile
from .json import validate_object
from .json import ValidationError
from .packages import Dependency
from .packages import Locker
from .packages import Package
from .packages import ProjectPackage
from .repositories import Pool
from .repositories.pypi_repository import PyPiRepository
from .spdx import license_by_id
from .utils._compat import Path
from .utils.toml_file import TomlFile


class Poetry:

    VERSION = __version__

    def __init__(
        self,
        file,  # type: Path
        local_config,  # type: dict
        package,  # type: Package
        locker,  # type: Locker
    ):
        self._file = TomlFile(file)
        self._package = package
        self._local_config = local_config
        self._locker = locker
        self._config = Config.create("config.toml")

        # Configure sources
        self._pool = Pool()
        for source in self._local_config.get("source", []):
            self._pool.configure(source)

        # Always put PyPI last to prefere private repositories
        self._pool.add_repository(PyPiRepository())

    @property
    def file(self):
        return self._file

    @property
    def package(self):  # type: () -> Package
        return self._package

    @property
    def local_config(self):  # type: () -> dict
        return self._local_config

    @property
    def locker(self):  # type: () -> Locker
        return self._locker

    @property
    def pool(self):  # type: () -> Pool
        return self._pool

    @classmethod
    def create(cls, cwd):  # type: (Path) -> Poetry
        candidates = [Path(cwd)]
        candidates.extend(Path(cwd).parents)

        for path in candidates:
            poetry_file = path / "pyproject.toml"

            if poetry_file.exists():
                break

        else:
            raise RuntimeError(
                "Poetry could not find a pyproject.toml file in {} or its parents".format(
                    cwd
                )
            )

        local_config = TomlFile(poetry_file.as_posix()).read()
        if "tool" not in local_config or "poetry" not in local_config["tool"]:
            raise RuntimeError(
                "[tool.poetry] section not found in {}".format(poetry_file.name)
            )
        local_config = local_config["tool"]["poetry"]

        # Checking validity
        cls.check(local_config)

        # Load package
        name = local_config["name"]
        version = local_config["version"]
        package = ProjectPackage(name, version, version)
        package.root_dir = poetry_file.parent

        for author in local_config["authors"]:
            package.authors.append(author)

        package.description = local_config.get("description", "")
        package.homepage = local_config.get("homepage")
        package.repository_url = local_config.get("repository")
        package.license = local_config.get("license")
        package.keywords = local_config.get("keywords", [])
        package.classifiers = local_config.get("classifiers", [])

        if "readme" in local_config:
            package.readme = Path(poetry_file.parent) / local_config["readme"]

        if "platform" in local_config:
            package.platform = local_config["platform"]

        if "dependencies" in local_config:
            for name, constraint in local_config["dependencies"].items():
                if name.lower() == "python":
                    package.python_versions = constraint
                    continue

                package.add_dependency(name, constraint)

        if "dev-dependencies" in local_config:
            for name, constraint in local_config["dev-dependencies"].items():
                package.add_dependency(name, constraint, category="dev")

        extras = local_config.get("extras", {})
        for extra_name, requirements in extras.items():
            package.extras[extra_name] = []

            # Checking for dependency
            for req in requirements:
                req = Dependency(req, "*")

                for dep in package.requires:
                    if dep.name == req.name:
                        dep.in_extras.append(extra_name)
                        package.extras[extra_name].append(dep)

                        break

        if "build" in local_config:
            package.build = local_config["build"]

        if "include" in local_config:
            package.include = local_config["include"]

        if "exclude" in local_config:
            package.exclude = local_config["exclude"]

        if "packages" in local_config:
            package.packages = local_config["packages"]

        locker = Locker(poetry_file.with_suffix(".lock"), local_config)

        return cls(poetry_file, local_config, package, locker)

    @classmethod
    def check(cls, config, strict=False):  # type: (dict, bool) -> bool
        """
        Checks the validity of a configuration
        """
        try:
            validate_object(config, "poetry-schema")
        except ValidationError as e:
            raise InvalidProjectFile(str(e))

        if strict:
            # If strict, check the file more thoroughly

            # Checking license
            license = config.get("license")
            if license:
                try:
                    license_by_id(license)
                except ValueError:
                    raise InvalidProjectFile("Invalid license")

        return True
