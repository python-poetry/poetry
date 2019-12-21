from __future__ import absolute_import
from __future__ import unicode_literals

import shutil

from typing import Dict
from typing import List
from typing import Optional

from clikit.api.io.io import IO

from .config.config import Config
from .config.file_config_source import FileConfigSource
from .io.null_io import NullIO
from .json import validate_object
from .locations import CONFIG_DIR
from .packages.dependency import Dependency
from .packages.locker import Locker
from .packages.project_package import ProjectPackage
from .poetry import Poetry
from .repositories.pypi_repository import PyPiRepository
from .spdx import license_by_id
from .utils._compat import Path
from .utils.toml_file import TomlFile


class Factory:
    """
    Factory class to create various elements needed by Poetry.
    """

    def create_poetry(
        self, cwd=None, io=None
    ):  # type: (Optional[Path], Optional[IO]) -> Poetry
        if io is None:
            io = NullIO()

        poetry_file = self.locate(cwd)

        local_config = TomlFile(poetry_file.as_posix()).read()
        if "tool" not in local_config or "poetry" not in local_config["tool"]:
            raise RuntimeError(
                "[tool.poetry] section not found in {}".format(poetry_file.name)
            )
        local_config = local_config["tool"]["poetry"]

        # Checking validity
        check_result = self.validate(local_config)
        if check_result["errors"]:
            message = ""
            for error in check_result["errors"]:
                message += "  - {}\n".format(error)

            raise RuntimeError("The Poetry configuration is invalid:\n" + message)

        # Load package
        name = local_config["name"]
        version = local_config["version"]
        package = ProjectPackage(name, version, version)
        package.root_dir = poetry_file.parent

        for author in local_config["authors"]:
            package.authors.append(author)

        for maintainer in local_config.get("maintainers", []):
            package.maintainers.append(maintainer)

        package.description = local_config.get("description", "")
        package.homepage = local_config.get("homepage")
        package.repository_url = local_config.get("repository")
        package.documentation_url = local_config.get("documentation")
        try:
            license_ = license_by_id(local_config.get("license", ""))
        except ValueError:
            license_ = None

        package.license = license_
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

                if isinstance(constraint, list):
                    for _constraint in constraint:
                        package.add_dependency(name, _constraint)

                    continue

                package.add_dependency(name, constraint)

        if "dev-dependencies" in local_config:
            for name, constraint in local_config["dev-dependencies"].items():
                if isinstance(constraint, list):
                    for _constraint in constraint:
                        package.add_dependency(name, _constraint, category="dev")

                    continue

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

        # Custom urls
        if "urls" in local_config:
            package.custom_urls = local_config["urls"]

        # Moving lock if necessary (pyproject.lock -> poetry.lock)
        lock = poetry_file.parent / "poetry.lock"
        if not lock.exists():
            # Checking for pyproject.lock
            old_lock = poetry_file.with_suffix(".lock")
            if old_lock.exists():
                shutil.move(str(old_lock), str(lock))

        locker = Locker(poetry_file.parent / "poetry.lock", local_config)

        # Loading global configuration
        config = self.create_config(io)

        # Loading local configuration
        local_config_file = TomlFile(poetry_file.parent / "poetry.toml")
        if local_config_file.exists():
            if io.is_debug():
                io.write_line(
                    "Loading configuration file {}".format(local_config_file.path)
                )

            config.merge(local_config_file.read())

        poetry = Poetry(poetry_file, local_config, package, locker, config)

        # Configuring sources
        for source in local_config.get("source", []):
            repository = self.create_legacy_repository(source, config)
            is_default = source.get("default", False)
            is_secondary = source.get("secondary", False)
            if io.is_debug():
                message = "Adding repository {} ({})".format(
                    repository.name, repository.url
                )
                if is_default:
                    message += " and setting it as the default one"
                elif is_secondary:
                    message += " and setting it as secondary"

                io.write_line(message)

            poetry.pool.add_repository(repository, is_default, secondary=is_secondary)

        # Always put PyPI last to prefer private repositories
        # but only if we have no other default source
        if not poetry.pool.has_default():
            poetry.pool.add_repository(PyPiRepository(), True)
        else:
            if io.is_debug():
                io.write_line("Deactivating the PyPI repository")

        return poetry

    @classmethod
    def create_config(cls, io=None):  # type: (Optional[IO]) -> Config
        if io is None:
            io = NullIO()

        config = Config()
        # Load global config
        config_file = TomlFile(Path(CONFIG_DIR) / "config.toml")
        if config_file.exists():
            if io.is_debug():
                io.write_line(
                    "<debug>Loading configuration file {}</debug>".format(
                        config_file.path
                    )
                )

            config.merge(config_file.read())

        config.set_config_source(FileConfigSource(config_file))

        # Load global auth config
        auth_config_file = TomlFile(Path(CONFIG_DIR) / "auth.toml")
        if auth_config_file.exists():
            if io.is_debug():
                io.write_line(
                    "<debug>Loading configuration file {}</debug>".format(
                        auth_config_file.path
                    )
                )

            config.merge(auth_config_file.read())

        config.set_auth_config_source(FileConfigSource(auth_config_file))

        return config

    def create_legacy_repository(
        self, source, auth_config
    ):  # type: (Dict[str, str], Config) -> LegacyRepository
        from .repositories.auth import Auth
        from .repositories.legacy_repository import LegacyRepository
        from .utils.helpers import get_client_cert, get_cert
        from .utils.password_manager import PasswordManager

        if "url" in source:
            # PyPI-like repository
            if "name" not in source:
                raise RuntimeError("Missing [name] in source.")
        else:
            raise RuntimeError("Unsupported source specified")

        password_manager = PasswordManager(auth_config)
        name = source["name"]
        url = source["url"]
        credentials = password_manager.get_http_auth(name)
        if credentials:
            auth = Auth(url, credentials["username"], credentials["password"])
        else:
            auth = None

        return LegacyRepository(
            name,
            url,
            auth=auth,
            cert=get_cert(auth_config, name),
            client_cert=get_client_cert(auth_config, name),
        )

    @classmethod
    def validate(
        cls, config, strict=False
    ):  # type: (dict, bool) -> Dict[str, List[str]]
        """
        Checks the validity of a configuration
        """
        result = {"errors": [], "warnings": []}
        # Schema validation errors
        validation_errors = validate_object(config, "poetry-schema")

        result["errors"] += validation_errors

        if strict:
            # If strict, check the file more thoroughly

            # Checking license
            license = config.get("license")
            if license:
                try:
                    license_by_id(license)
                except ValueError:
                    result["errors"].append("{} is not a valid license".format(license))

            if "dependencies" in config:
                python_versions = config["dependencies"]["python"]
                if python_versions == "*":
                    result["warnings"].append(
                        "A wildcard Python dependency is ambiguous. "
                        "Consider specifying a more explicit one."
                    )

                for name, constraint in config["dependencies"].items():
                    if not isinstance(constraint, dict):
                        continue

                    if "allows-prereleases" in constraint:
                        result["warnings"].append(
                            'The "{}" dependency specifies '
                            'the "allows-prereleases" property, which is deprecated. '
                            'Use "allow-prereleases" instead.'.format(name)
                        )

            # Checking for scripts with extras
            if "scripts" in config:
                scripts = config["scripts"]
                for name, script in scripts.items():
                    if not isinstance(script, dict):
                        continue

                    extras = script["extras"]
                    for extra in extras:
                        if extra not in config["extras"]:
                            result["errors"].append(
                                'Script "{}" requires extra "{}" which is not defined.'.format(
                                    name, extra
                                )
                            )

        return result

    @classmethod
    def locate(cls, cwd):  # type: (Path) -> Path
        candidates = [Path(cwd)]
        candidates.extend(Path(cwd).parents)

        for path in candidates:
            poetry_file = path / "pyproject.toml"

            if poetry_file.exists():
                return poetry_file

        else:
            raise RuntimeError(
                "Poetry could not find a pyproject.toml file in {} or its parents".format(
                    cwd
                )
            )
