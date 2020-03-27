from tomlkit import dumps
from tomlkit import loads
from tomlkit import table

from poetry.utils.helpers import module_name


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

BUILD_SYSTEM_MIN_VERSION = "0.12"
BUILD_SYSTEM_MAX_VERSION = None


class Layout(object):
    def __init__(
        self,
        project,
        version="0.1.0",
        description="",
        readme_format="md",
        author=None,
        license=None,
        python="*",
        dependencies=None,
        dev_dependencies=None,
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

    def create(self, path, with_tests=True):
        path.mkdir(parents=True, exist_ok=True)

        self._create_default(path)
        self._create_readme(path)

        if with_tests:
            self._create_tests(path)

        self._write_poetry(path)

    def generate_poetry_content(self):
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

        build_system.add("requires", ["poetry" + build_system_version])
        build_system.add("build-backend", "poetry.masonry.api")

        content.add("build-system", build_system)

        return dumps(content)

    def _create_default(self, path, src=True):
        raise NotImplementedError()

    def _create_readme(self, path):
        if self._readme_format == "rst":
            readme_file = path / "README.rst"
        else:
            readme_file = path / "README.md"

        readme_file.touch()

    def _create_tests(self, path):
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

    def _write_poetry(self, path):
        content = self.generate_poetry_content()

        poetry = path / "pyproject.toml"

        with poetry.open("w", encoding="utf-8") as f:
            f.write(content)
