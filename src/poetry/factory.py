from __future__ import annotations

import contextlib
import logging
import re

from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from cleo.io.null_io import NullIO
from poetry.core.factory import Factory as BaseFactory
from poetry.core.packages.dependency_group import MAIN_GROUP
from poetry.core.packages.project_package import ProjectPackage
from poetry.core.toml.file import TOMLFile

from poetry.config.config import Config
from poetry.json import validate_object
from poetry.packages.locker import Locker
from poetry.plugins.plugin import Plugin
from poetry.plugins.plugin_manager import PluginManager
from poetry.poetry import Poetry


if TYPE_CHECKING:
    from pathlib import Path

    from cleo.io.io import IO
    from poetry.core.packages.package import Package
    from tomlkit.toml_document import TOMLDocument

    from poetry.repositories.legacy_repository import LegacyRepository
    from poetry.utils.dependency_specification import DependencySpec


logger = logging.getLogger(__name__)


class Factory(BaseFactory):
    """
    Factory class to create various elements needed by Poetry.
    """

    def create_poetry(
        self,
        cwd: Path | None = None,
        with_groups: bool = True,
        io: IO | None = None,
        disable_plugins: bool = False,
        disable_cache: bool = False,
    ) -> Poetry:
        if io is None:
            io = NullIO()

        base_poetry = super().create_poetry(cwd=cwd, with_groups=with_groups)

        locker = Locker(
            base_poetry.file.parent / "poetry.lock", base_poetry.local_config
        )

        # Loading global configuration
        config = Config.create()

        # Loading local configuration
        local_config_file = TOMLFile(base_poetry.file.parent / "poetry.toml")
        if local_config_file.exists():
            if io.is_debug():
                io.write_line(f"Loading configuration file {local_config_file.path}")

            config.merge(local_config_file.read())

        # Load local sources
        repositories = {}
        existing_repositories = config.get("repositories", {})
        for source in base_poetry.pyproject.poetry_config.get("source", []):
            name = source.get("name")
            url = source.get("url")
            if name and url and name not in existing_repositories:
                repositories[name] = {"url": url}

        config.merge({"repositories": repositories})

        poetry = Poetry(
            base_poetry.file.path,
            base_poetry.local_config,
            base_poetry.package,
            locker,
            config,
            disable_cache,
        )

        # Configuring sources
        self.configure_sources(
            poetry,
            poetry.local_config.get("source", []),
            config,
            io,
            disable_cache=disable_cache,
        )

        plugin_manager = PluginManager(Plugin.group, disable_plugins=disable_plugins)
        plugin_manager.load_plugins()
        poetry.set_plugin_manager(plugin_manager)
        plugin_manager.activate(poetry, io)

        return poetry

    @classmethod
    def get_package(cls, name: str, version: str) -> ProjectPackage:
        return ProjectPackage(name, version, version)

    @classmethod
    def configure_sources(
        cls,
        poetry: Poetry,
        sources: list[dict[str, str]],
        config: Config,
        io: IO,
        disable_cache: bool = False,
    ) -> None:
        if disable_cache:
            logger.debug("Disabling source caches")

        for source in sources:
            repository = cls.create_package_source(
                source, config, disable_cache=disable_cache
            )
            is_default = bool(source.get("default", False))
            is_secondary = bool(source.get("secondary", False))
            if io.is_debug():
                message = f"Adding repository {repository.name} ({repository.url})"
                if is_default:
                    message += " and setting it as the default one"
                elif is_secondary:
                    message += " and setting it as secondary"

                io.write_line(message)

            poetry.pool.add_repository(repository, is_default, secondary=is_secondary)

        # Put PyPI last to prefer private repositories
        # unless we have no default source AND no primary sources
        # (default = false, secondary = false)
        if poetry.pool.has_default():
            if io.is_debug():
                io.write_line("Deactivating the PyPI repository")
        else:
            from poetry.repositories.pypi_repository import PyPiRepository

            default = not poetry.pool.has_primary_repositories()
            poetry.pool.add_repository(
                PyPiRepository(disable_cache=disable_cache), default, not default
            )

    @classmethod
    def create_package_source(
        cls, source: dict[str, str], auth_config: Config, disable_cache: bool = False
    ) -> LegacyRepository:
        from poetry.repositories.legacy_repository import LegacyRepository
        from poetry.repositories.single_page_repository import SinglePageRepository

        if "url" not in source:
            raise RuntimeError("Unsupported source specified")

        # PyPI-like repository
        if "name" not in source:
            raise RuntimeError("Missing [name] in source.")
        name = source["name"]
        url = source["url"]

        repository_class = LegacyRepository

        if re.match(r".*\.(htm|html)$", url):
            repository_class = SinglePageRepository

        return repository_class(
            name,
            url,
            config=auth_config,
            disable_cache=disable_cache,
        )

    @classmethod
    def create_pyproject_from_package(
        cls, package: Package, path: Path | None = None
    ) -> TOMLDocument:
        import tomlkit

        from poetry.utils.dependency_specification import dependency_to_specification

        pyproject: dict[str, Any] = tomlkit.document()

        pyproject["tool"] = tomlkit.table(is_super_table=True)

        content: dict[str, Any] = tomlkit.table()
        pyproject["tool"]["poetry"] = content

        content["name"] = package.name
        content["version"] = package.version.text
        content["description"] = package.description
        content["authors"] = package.authors
        content["license"] = package.license.id if package.license else ""

        if package.classifiers:
            content["classifiers"] = package.classifiers

        for key, attr in {
            ("documentation", "documentation_url"),
            ("repository", "repository_url"),
            ("homepage", "homepage"),
            ("maintainers", "maintainers"),
            ("keywords", "keywords"),
        }:
            value = getattr(package, attr, None)
            if value:
                content[key] = value

        readmes = []

        for readme in package.readmes:
            readme_posix_path = readme.as_posix()

            with contextlib.suppress(ValueError):
                if package.root_dir:
                    readme_posix_path = readme.relative_to(package.root_dir).as_posix()

            readmes.append(readme_posix_path)

        if readmes:
            content["readme"] = readmes

        optional_dependencies = set()
        extras_section = None

        if package.extras:
            extras_section = tomlkit.table()

            for extra in package.extras:
                _dependencies = []
                for dependency in package.extras[extra]:
                    _dependencies.append(dependency.name)
                    optional_dependencies.add(dependency.name)

                extras_section[extra] = _dependencies

        optional_dependencies = set(optional_dependencies)
        dependency_section = content["dependencies"] = tomlkit.table()
        dependency_section["python"] = package.python_versions

        for dep in package.all_requires:
            constraint: DependencySpec | str = dependency_to_specification(
                dep, tomlkit.inline_table()
            )

            if not isinstance(constraint, str):
                if dep.name in optional_dependencies:
                    constraint["optional"] = True

                if len(constraint) == 1 and "version" in constraint:
                    assert isinstance(constraint["version"], str)
                    constraint = constraint["version"]
                elif not constraint:
                    constraint = "*"

            for group in dep.groups:
                if group == MAIN_GROUP:
                    dependency_section[dep.name] = constraint
                else:
                    if "group" not in content:
                        content["group"] = tomlkit.table(is_super_table=True)

                    if group not in content["group"]:
                        content["group"][group] = tomlkit.table(is_super_table=True)

                    if "dependencies" not in content["group"][group]:
                        content["group"][group]["dependencies"] = tomlkit.table()

                    content["group"][group]["dependencies"][dep.name] = constraint

        if extras_section:
            content["extras"] = extras_section

        pyproject = cast("TOMLDocument", pyproject)
        pyproject.add(tomlkit.nl())

        if path:
            path.joinpath("pyproject.toml").write_text(
                pyproject.as_string(), encoding="utf-8"
            )

        return pyproject

    @classmethod
    def validate(
        cls, config: dict[str, Any], strict: bool = False
    ) -> dict[str, list[str]]:
        results = super().validate(config, strict)

        results["errors"].extend(validate_object(config))

        return results
