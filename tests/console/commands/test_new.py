from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.factory import Factory
from tests.helpers import get_package


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from poetry.poetry import Poetry
    from tests.helpers import TestRepository
    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("new")


def verify_project_directory(
    path: Path,
    package_name: str,
    package_path: str,
    include_from: str | None = None,
) -> Poetry:
    package_path = Path(package_path)
    assert path.is_dir()

    pyproject = path / "pyproject.toml"
    assert pyproject.is_file()

    init_file = path / package_path / "__init__.py"
    assert init_file.is_file()

    tests_init_file = path / "tests" / "__init__.py"
    assert tests_init_file.is_file()

    poetry = Factory().create_poetry(cwd=path)
    assert poetry.package.name == package_name

    if include_from:
        package_include = {
            "include": package_path.relative_to(include_from).parts[0],
            "from": include_from,
        }
    else:
        package_include = {"include": package_path.parts[0]}

    packages = poetry.local_config.get("packages")

    if not packages:
        assert poetry.local_config.get("name") == package_include.get("include")
    else:
        assert len(packages) == 1
        assert packages[0] == package_include

    return poetry


@pytest.mark.parametrize(
    "options,directory,package_name,package_path,include_from",
    [
        ([], "package", "package", "package", None),
        (["--src"], "package", "package", "src/package", "src"),
        (
            ["--name namespace.package"],
            "namespace-package",
            "namespace-package",
            "namespace/package",
            None,
        ),
        (
            ["--src", "--name namespace.package"],
            "namespace-package",
            "namespace-package",
            "src/namespace/package",
            "src",
        ),
        (
            ["--name namespace.package_a"],
            "namespace-package_a",
            "namespace-package-a",
            "namespace/package_a",
            None,
        ),
        (
            ["--src", "--name namespace.package_a"],
            "namespace-package_a",
            "namespace-package-a",
            "src/namespace/package_a",
            "src",
        ),
        (
            ["--name namespace_package"],
            "namespace-package",
            "namespace-package",
            "namespace_package",
            None,
        ),
        (
            ["--name namespace_package", "--src"],
            "namespace-package",
            "namespace-package",
            "src/namespace_package",
            "src",
        ),
        (
            ["--name namespace.package"],
            "package",
            "namespace-package",
            "namespace/package",
            None,
        ),
        (
            ["--name namespace.package", "--src"],
            "package",
            "namespace-package",
            "src/namespace/package",
            "src",
        ),
        (
            ["--name namespace.package"],
            "package",
            "namespace-package",
            "namespace/package",
            None,
        ),
        (
            ["--name namespace.package", "--src"],
            "package",
            "namespace-package",
            "src/namespace/package",
            "src",
        ),
        ([], "namespace_package", "namespace-package", "namespace_package", None),
        (
            ["--src", "--name namespace_package"],
            "namespace_package",
            "namespace-package",
            "src/namespace_package",
            "src",
        ),
    ],
)
def test_command_new(
    options: list[str],
    directory: str,
    package_name: str,
    package_path: str,
    include_from: str | None,
    tester: CommandTester,
    tmp_dir: str,
):
    path = Path(tmp_dir) / directory
    options.append(path.as_posix())
    tester.execute(" ".join(options))
    verify_project_directory(path, package_name, package_path, include_from)


@pytest.mark.parametrize(("fmt",), [(None,), ("md",), ("rst",), ("adoc",), ("creole",)])
def test_command_new_with_readme(fmt: str | None, tester: CommandTester, tmp_dir: str):
    package = "package"
    path = Path(tmp_dir) / package
    options = [path.as_posix()]

    if fmt:
        options.insert(0, f"--readme {fmt}")

    tester.execute(" ".join(options))

    poetry = verify_project_directory(path, package, package, None)
    assert poetry.local_config.get("readme") == f"README.{fmt or 'md'}"


def test_command_new_with_dependencies(
    tester: CommandTester, repo: TestRepository, tmp_dir: str
):
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))
    tester.command._repository = repo

    package_path = "custompackage"
    path = Path(tmp_dir) / package_path
    options = [
        path.as_posix(),
        "--name custompackage",
        "--package-version 1.2.3",
        "--description 'My Description'",
        "--author 'Your Name <you@example.com>' ",
        "--license 'My License'",
        "--python '^3.8' ",
        "--dependency pendulum",
    ]
    tester.execute(" ".join(options))
    poetry = verify_project_directory(path, "custompackage", package_path, None)

    expected = """\
[tool.poetry]
name = "custompackage"
version = "1.2.3"
description = "My Description"
authors = ["Your Name <you@example.com>"]
license = "My License"
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.8"
pendulum = "^2.0.0"
"""
    # Replacing possible \r\n because as_string adds them on Windows
    assert expected in poetry.pyproject.data.as_string().replace("\r\n", "\n")
