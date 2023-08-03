from __future__ import annotations

import subprocess
import sys

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest

from poetry.core.utils.helpers import module_name

from poetry.factory import Factory


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.config.config import Config
    from poetry.poetry import Poetry
    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("new")


def verify_project_directory(
    path: Path,
    package_name: str,
    package_path: str | Path,
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

    name = poetry.local_config.get("name", "")
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
    tmp_path: Path,
) -> None:
    path = tmp_path / directory
    options.append(str(path))
    tester.execute(" ".join(options))
    verify_project_directory(path, package_name, package_path, include_from)


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

    poetry = verify_project_directory(path, package, package, None)
    assert poetry.local_config.get("readme") == f"README.{fmt or 'md'}"


@pytest.mark.parametrize(
    ["prefer_active", "python"],
    [
        (True, "1.1"),
        (False, f"{sys.version_info[0]}.{sys.version_info[1]}"),
    ],
)
def test_respect_prefer_active_on_new(
    prefer_active: bool,
    python: str,
    config: Config,
    mocker: MockerFixture,
    tester: CommandTester,
    tmp_path: Path,
) -> None:
    from poetry.utils.env import GET_PYTHON_VERSION_ONELINER

    orig_check_output = subprocess.check_output

    def mock_check_output(cmd: str, *_: Any, **__: Any) -> str:
        if GET_PYTHON_VERSION_ONELINER in cmd:
            return "1.1.1"

        output: str = orig_check_output(cmd, *_, **__)
        return output

    mocker.patch("subprocess.check_output", side_effect=mock_check_output)

    config.config["virtualenvs"]["prefer-active-python"] = prefer_active

    package = "package"
    path = tmp_path / package
    options = [str(path)]
    tester.execute(" ".join(options))

    pyproject_file = path / "pyproject.toml"

    expected = f"""\
[tool.poetry.dependencies]
python = "^{python}"
"""

    assert expected in pyproject_file.read_text()
