from __future__ import annotations

import sys

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.core.utils.helpers import module_name

from poetry.factory import Factory


if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from cleo.testers.command_tester import CommandTester

    from poetry.config.config import Config
    from poetry.poetry import Poetry
    from tests.types import CommandTesterFactory
    from tests.types import MockedPythonRegister


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("new")


def verify_project_directory(
    path: Path,
    package_name: str,
    package_path: str | Path,
    is_flat: bool = False,
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

    if is_flat:
        package_include = {"include": package_path.parts[0]}
    else:
        package_include = {
            "include": package_path.relative_to("src").parts[0],
            "from": "src",
        }

    name = poetry.package.name
    packages = poetry.local_config.get("packages")

    if not packages:
        assert module_name(name) == package_include.get("include")
    else:
        assert len(packages) == 1
        assert packages[0] == package_include

    return poetry


@pytest.mark.parametrize(
    "options,directory,package_name,package_path,include_from",
    [
        (["--flat"], "package", "package", "package", None),
        ([], "package", "package", "src/package", "src"),
        (
            ["--flat", "--name namespace.package"],
            "namespace-package",
            "namespace-package",
            "namespace/package",
            None,
        ),
        (
            ["--name namespace.package"],
            "namespace-package",
            "namespace-package",
            "src/namespace/package",
            "src",
        ),
        (
            ["--flat", "--name namespace.package_a"],
            "namespace-package_a",
            "namespace-package-a",
            "namespace/package_a",
            None,
        ),
        (
            ["--name namespace.package_a"],
            "namespace-package_a",
            "namespace-package-a",
            "src/namespace/package_a",
            "src",
        ),
        (
            ["--flat", "--name namespace_package"],
            "namespace-package",
            "namespace-package",
            "namespace_package",
            None,
        ),
        (
            ["--name namespace_package"],
            "namespace-package",
            "namespace-package",
            "src/namespace_package",
            "src",
        ),
        (
            ["--flat", "--name namespace.package"],
            "package",
            "namespace-package",
            "namespace/package",
            None,
        ),
        (
            ["--name namespace.package"],
            "package",
            "namespace-package",
            "src/namespace/package",
            "src",
        ),
        (
            ["--name namespace.package", "--flat"],
            "package",
            "namespace-package",
            "namespace/package",
            None,
        ),
        (
            ["--name namespace.package"],
            "package",
            "namespace-package",
            "src/namespace/package",
            "src",
        ),
        (
            ["--flat"],
            "namespace_package",
            "namespace-package",
            "namespace_package",
            None,
        ),
        (
            ["--name namespace_package"],
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
    tmp_path: Path,
) -> None:
    path = tmp_path / directory
    options.append(str(path))
    tester.execute(" ".join(options))
    verify_project_directory(path, package_name, package_path, "--flat" in options)


@pytest.mark.parametrize(("fmt",), [(None,), ("md",), ("rst",), ("adoc",), ("creole",)])
def test_command_new_with_readme(
    fmt: str | None, tester: CommandTester, tmp_path: Path
) -> None:
    package = "package"
    path = tmp_path / package
    options = [path.as_posix()]

    if fmt:
        options.insert(0, f"--readme {fmt}")

    tester.execute(" ".join(options))

    poetry = verify_project_directory(path, package, Path("src") / package)
    project_section = poetry.pyproject.data["project"]
    assert isinstance(project_section, dict)
    assert project_section["readme"] == f"README.{fmt or 'md'}"


@pytest.mark.parametrize(
    ["use_poetry_python", "python"],
    [
        (False, "1.1"),
        (True, f"{sys.version_info[0]}.{sys.version_info[1]}"),
    ],
)
def test_respect_use_poetry_python_on_new(
    use_poetry_python: bool,
    python: str,
    config: Config,
    tester: CommandTester,
    tmp_path: Path,
    mocked_python_register: MockedPythonRegister,
    with_no_active_python: MagicMock,
) -> None:
    mocked_python_register(f"{python}.1", make_system=True)
    config.config["virtualenvs"]["use-poetry-python"] = use_poetry_python

    package = "package"
    path = tmp_path / package
    options = [str(path)]
    tester.execute(" ".join(options))

    pyproject_file = path / "pyproject.toml"

    expected = f"""\
requires-python = ">={python}"
"""

    assert expected in pyproject_file.read_text(encoding="utf-8")


def test_basic_interactive_new(
    tester: CommandTester, tmp_path: Path, init_basic_inputs: str, new_basic_toml: str
) -> None:
    path = tmp_path / "somepackage"
    tester.execute(f"--interactive {path.as_posix()}", inputs=init_basic_inputs)
    verify_project_directory(path, "my-package", "src/my_package")
    assert new_basic_toml in tester.io.fetch_output()


def test_new_creates_structure_in_empty_existing_directory(
    tester: CommandTester, tmp_path: Path
) -> None:
    """Test that poetry new creates structure in existing but empty directory."""
    # Create empty directory
    package_dir = tmp_path / "my-package"
    package_dir.mkdir()

    tester.execute(str(package_dir))

    # Should create full project structure
    verify_project_directory(package_dir, "my-package", "src/my_package")

    assert (package_dir / "tests").exists()
    assert (package_dir / "src" / "my_package").exists()
    assert (package_dir / "pyproject.toml").exists()
    assert (package_dir / "README.md").exists()


def test_new_with_dot_in_empty_directory(tester: CommandTester, tmp_path: Path) -> None:
    """Test that poetry new . works in empty directory and creates structure."""
    import os

    test_dir = "test_new_with_dot_in_empty_directory"

    # Change to the temporary directory
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    os.mkdir(test_dir)
    tmp_path = Path(original_cwd) / test_dir
    os.chdir(tmp_path)

    try:
        tester.execute(".")

        # Should create full project structure
        assert (tmp_path / "tests").exists()
        assert (tmp_path / "src").exists()
        assert (tmp_path / "pyproject.toml").exists()
        assert (tmp_path / "README.md").exists()
    finally:
        # Always restore original directory
        os.chdir(original_cwd)
