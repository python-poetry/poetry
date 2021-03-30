from typing import TYPE_CHECKING
from typing import Dict
from typing import Optional

from tomlkit import dumps
from tomlkit import loads
from tomlkit import table

from poetry.utils.helpers import module_name


if TYPE_CHECKING:
    from pathlib import Path

    from poetry.core.pyproject.toml import PyProjectTOML

TESTS_DEFAULT = u"""from {package_name} import __version__


def test_version():
    assert __version__ == '{version}'
"""


POETRY_DEFAULT = """\
[tool.poetry]
name = ""
version = ""
description = ""
authors = []

[tool.poetry.dependencies]

[tool.poetry.dev-dependencies]
"""

POETRY_WITH_LICENSE = """\
[tool.poetry]
name = ""
version = ""
description = ""
authors = []
license = ""

[tool.poetry.dependencies]

[tool.poetry.dev-dependencies]
"""

BUILD_SYSTEM_MIN_VERSION = "1.0.0"
BUILD_SYSTEM_MAX_VERSION: Optional[str] = None


class Layout(object):
    def __init__(
        self,
        project: str,
        version: str = "0.1.0",
        description: str = "",
        readme_format: str = "md",
        author: Optional[str] = None,
        license: Optional[str] = None,
        python: str = "*",
        dependencies: Optional[Dict[str, str]] = None,
        dev_dependencies: Optional[Dict[str, str]] = None,
    ):
        self._project = project
        self._package_name = module_name(project)
        self._version = version
        self._description = description
        self._readme_format = readme_format
        self._license = license
        self._python = python
        self._dependencies = dependencies or {}
        self._dev_dependencies = dev_dependencies or {}

        if not author:
            author = "Your Name <you@example.com>"

        self._author = author

    def create(self, path: "Path", with_tests: bool = True) -> None:
        path.mkdir(parents=True, exist_ok=True)

        self._create_default(path)
        self._create_readme(path)

        if with_tests:
            self._create_tests(path)

        self._write_poetry(path)

    def generate_poetry_content(
        self, original: Optional["PyProjectTOML"] = None
    ) -> str:
        template = POETRY_DEFAULT
        if self._license:
            template = POETRY_WITH_LICENSE

        content = loads(template)
        poetry_content = content["tool"]["poetry"]
        poetry_content["name"] = self._project
        poetry_content["version"] = self._version
        poetry_content["description"] = self._description
        poetry_content["authors"].append(self._author)
        if self._license:
            poetry_content["license"] = self._license

        poetry_content["dependencies"]["python"] = self._python

        for dep_name, dep_constraint in self._dependencies.items():
            poetry_content["dependencies"][dep_name] = dep_constraint

        for dep_name, dep_constraint in self._dev_dependencies.items():
            poetry_content["dev-dependencies"][dep_name] = dep_constraint

        # Add build system
        build_system = table()
        build_system_version = ">=" + BUILD_SYSTEM_MIN_VERSION
        if BUILD_SYSTEM_MAX_VERSION is not None:
            build_system_version += ",<" + BUILD_SYSTEM_MAX_VERSION

        build_system.add("requires", ["poetry-core" + build_system_version])
        build_system.add("build-backend", "poetry.core.masonry.api")

        content.add("build-system", build_system)

        content = dumps(content)

        if original and original.file.exists():
            content = dumps(original.data) + "\n" + content

        return content

    def _create_default(self, path: "Path", src: bool = True) -> None:
        raise NotImplementedError()

    def _create_readme(self, path: "Path") -> None:
        if self._readme_format == "rst":
            readme_file = path / "README.rst"
        else:
            readme_file = path / "README.md"

        readme_file.touch()

    def _create_tests(self, path: "Path") -> None:
        tests = path / "tests"
        tests_init = tests / "__init__.py"
        tests_default = tests / "test_{}.py".format(self._package_name)

        tests.mkdir()
        tests_init.touch(exist_ok=False)

        with tests_default.open("w", encoding="utf-8") as f:
            f.write(
                TESTS_DEFAULT.format(
                    package_name=self._package_name, version=self._version
                )
            )

    def _write_poetry(self, path: "Path") -> None:
        content = self.generate_poetry_content()

        poetry = path / "pyproject.toml"

        with poetry.open("w", encoding="utf-8") as f:
            f.write(content)
