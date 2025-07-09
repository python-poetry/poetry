from __future__ import annotations

import importlib.metadata

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from packaging.utils import canonicalize_name
from poetry.core.constraints.version import Version
from poetry.core.utils.helpers import module_name
from poetry.core.utils.patterns import AUTHOR_REGEX
from tomlkit import inline_table
from tomlkit import loads
from tomlkit import table
from tomlkit.toml_document import TOMLDocument

from poetry.factory import Factory
from poetry.pyproject.toml import PyProjectTOML


if TYPE_CHECKING:
    from collections.abc import Mapping

    from tomlkit.items import InlineTable


POETRY_DEFAULT = """\
[project]
name = ""
version = ""
description = ""
authors = [
]
license = {}
readme = ""
requires-python = ""
dependencies = [
]

[tool.poetry]
packages = []

[tool.poetry.group.dev.dependencies]
"""

POETRY_TOOL_ONLY = """\
[tool.poetry]
name = ""
version = ""
description = ""
authors = [
]
license = ""
readme = ""
packages = []

[tool.poetry.dependencies]
python = ""

[tool.poetry.group.dev.dependencies]
"""

poetry_core_version = Version.parse(importlib.metadata.version("poetry-core"))

BUILD_SYSTEM_MIN_VERSION: str | None = Version.from_parts(
    major=poetry_core_version.major,
    minor=poetry_core_version.minor if poetry_core_version.major == 0 else 0,
    patch=poetry_core_version.patch
    if (poetry_core_version.major, poetry_core_version.minor) == (0, 0)
    else 0,
).to_string()
BUILD_SYSTEM_MAX_VERSION: str | None = poetry_core_version.next_breaking().to_string()


class Layout:
    def __init__(
        self,
        project: str,
        version: str = "0.1.0",
        description: str = "",
        readme_format: str = "md",
        author: str | None = None,
        license: str | None = None,
        python: str | None = None,
        dependencies: Mapping[str, str | Mapping[str, Any]] | None = None,
        dev_dependencies: Mapping[str, str | Mapping[str, Any]] | None = None,
        use_tool_poetry: bool = False,
    ) -> None:
        self._project = canonicalize_name(project)
        self._package_path_relative = Path(
            *(module_name(part) for part in project.split("."))
        )
        self._package_name = ".".join(self._package_path_relative.parts)
        self._version = version
        self._description = description

        self._readme_format = readme_format.lower()

        self._license = license
        self._python = python
        self._dependencies = dependencies or {}
        self._dev_dependencies = dev_dependencies or {}
        self._use_tool_poetry = use_tool_poetry

        if not author:
            author = "Your Name <you@example.com>"

        self._author = author

    @property
    def basedir(self) -> Path:
        return Path()

    @property
    def package_path(self) -> Path:
        return self.basedir / self._package_path_relative

    def get_package_include(self) -> InlineTable | None:
        package = inline_table()

        # If a project is created in the root directory (this is reasonable inside a
        # docker container, eg <https://github.com/python-poetry/poetry/issues/5103>)
        # then parts will be empty.
        parts = self._package_path_relative.parts
        if not parts:
            return None

        include = parts[0]
        package.append("include", include)

        if self.basedir != Path():
            package.append("from", self.basedir.as_posix())
        else:
            if module_name(self._project) == include:
                # package include and package name are the same,
                # packages table is redundant here.
                return None

        return package

    def create(
        self, path: Path, with_tests: bool = True, with_pyproject: bool = True
    ) -> None:
        path.mkdir(parents=True, exist_ok=True)

        self._create_default(path)
        self._create_readme(path)

        if with_tests:
            self._create_tests(path)

        if with_pyproject:
            self._write_poetry(path)

    def _set_metadata_fields(
        self, metadata_content: dict[str, Any], author_format: str = "object"
    ) -> None:
        metadata_content["name"] = self._project
        metadata_content["version"] = self._version
        metadata_content["description"] = self._description

        m = AUTHOR_REGEX.match(self._author)
        if m is None:
            raise ValueError(f"Invalid author: {self._author}")
        if author_format == "object":
            author_obj = {"name": m.group("name")}
            if email := m.group("email"):
                author_obj["email"] = email
            metadata_content["authors"].append(author_obj)
        else:
            author_str = f"{m.group('name')}"
            if email := m.group("email"):
                author_str += f" <{email}>"
            metadata_content["authors"].append(author_str)

        if self._license:
            if author_format == "object":
                metadata_content["license"]["text"] = self._license
            else:
                metadata_content["license"] = self._license
        else:
            metadata_content.pop("license", None)

        metadata_content["readme"] = f"README.{self._readme_format}"

    def _set_dependencies(
        self,
        dependencies_content: dict[str, Any],
        dev_dependencies_content: dict[str, Any],
    ) -> None:
        for dep_name, dep_constraint in self._dependencies.items():
            dependency = Factory.create_dependency(dep_name, dep_constraint)
            dependencies_content[dep_name] = dependency.to_pep_508()
        for dep_name, dep_constraint in self._dev_dependencies.items():
            dev_dependencies_content[dep_name] = dep_constraint

    def generate_project_content(self) -> TOMLDocument:
        template = POETRY_DEFAULT if not self._use_tool_poetry else POETRY_TOOL_ONLY
        content: dict[str, Any] = loads(template)

        if self._use_tool_poetry:
            poetry_content: dict[str, Any] = content["tool"]["poetry"]
            self._set_metadata_fields(poetry_content, author_format="string")
            if self._python:
                poetry_content["dependencies"]["python"] = self._python
            else:
                poetry_content["dependencies"].pop("python", None)
            self._set_dependencies(
                poetry_content["dependencies"],
                poetry_content["group"]["dev"]["dependencies"],
            )
            packages = self.get_package_include()
            if packages:
                poetry_content["packages"].append(packages)
            else:
                poetry_content.pop("packages", None)
            if self._dev_dependencies:
                self._set_dependencies(
                    {}, poetry_content["group"]["dev"]["dependencies"]
                )
            else:
                poetry_content.pop("group", None)
        else:
            project_content: dict[str, Any] = content["project"]
            self._set_metadata_fields(project_content, author_format="object")
            if self._python:
                project_content["requires-python"] = self._python
            else:
                project_content.pop("requires-python", None)
            project_content["dependencies"] = []
            for dep_name, dep_constraint in self._dependencies.items():
                dependency = Factory.create_dependency(dep_name, dep_constraint)
                project_content["dependencies"].append(dependency.to_pep_508())
            poetry_tool_content: dict[str, Any] = content["tool"]["poetry"]
            packages = self.get_package_include()
            if packages:
                poetry_tool_content["packages"].append(packages)
            else:
                poetry_tool_content.pop("packages", None)
            if self._dev_dependencies:
                self._set_dependencies(
                    {}, poetry_tool_content["group"]["dev"]["dependencies"]
                )
            else:
                poetry_tool_content.pop("group", None)
            if not poetry_tool_content:
                content["tool"].pop("poetry", None)
        # Add build system
        build_system = table()
        build_system_version: str = ""
        if BUILD_SYSTEM_MIN_VERSION is not None:
            build_system_version = ">=" + BUILD_SYSTEM_MIN_VERSION
        if BUILD_SYSTEM_MAX_VERSION is not None:
            if build_system_version:
                build_system_version += ","
            build_system_version += "<" + BUILD_SYSTEM_MAX_VERSION
        build_system.add("requires", ["poetry-core" + build_system_version])
        build_system.add("build-backend", "poetry.core.masonry.api")
        assert isinstance(content, TOMLDocument)
        content.add("build-system", build_system)
        return content

    def _create_default(self, path: Path, src: bool = True) -> None:
        package_path = path / self.package_path
        package_path.mkdir(parents=True)

        package_init = package_path / "__init__.py"
        package_init.touch()

    def _create_readme(self, path: Path) -> Path:
        readme_file = path.joinpath(f"README.{self._readme_format}")
        readme_file.touch()
        return readme_file

    @staticmethod
    def _create_tests(path: Path) -> None:
        tests = path / "tests"
        tests.mkdir()

        tests_init = tests / "__init__.py"
        tests_init.touch(exist_ok=False)

    def _write_poetry(self, path: Path) -> None:
        pyproject = PyProjectTOML(path / "pyproject.toml")
        content = self.generate_project_content()
        for section, item in content.items():
            pyproject.data.append(section, item)
        pyproject.save()
