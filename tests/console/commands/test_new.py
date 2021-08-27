from pathlib import Path
<<<<<<< HEAD
from typing import TYPE_CHECKING
from typing import List
=======
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
from typing import Optional

import pytest

from poetry.factory import Factory
<<<<<<< HEAD


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from poetry.poetry import Poetry
    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(command_tester_factory: "CommandTesterFactory") -> "CommandTester":
=======
from poetry.poetry import Poetry


@pytest.fixture
def tester(command_tester_factory):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return command_tester_factory("new")


def verify_project_directory(
    path: Path, package_name: str, package_path: str, include_from: Optional[str] = None
<<<<<<< HEAD
) -> "Poetry":
=======
) -> Poetry:
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
<<<<<<< HEAD
    options: List[str],
    directory: str,
    package_name: str,
    package_path: str,
    include_from: Optional[str],
    tester: "CommandTester",
    tmp_dir: str,
=======
    options, directory, package_name, package_path, include_from, tester, tmp_dir
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    path = Path(tmp_dir) / directory
    options.append(path.as_posix())
    tester.execute(" ".join(options))
    verify_project_directory(path, package_name, package_path, include_from)


<<<<<<< HEAD
@pytest.mark.parametrize(("fmt",), [(None,), ("md",), ("rst",)])
def test_command_new_with_readme(
    fmt: Optional[str], tester: "CommandTester", tmp_dir: str
):
    package = "package"
    path = Path(tmp_dir) / package
    options = [path.as_posix()]

    if fmt:
        options.insert(0, f"--readme {fmt}")

    tester.execute(" ".join(options))

    poetry = verify_project_directory(path, package, package, None)
    assert poetry.local_config.get("readme") == f"README.{fmt or 'md'}"
=======
@pytest.mark.parametrize("fmt", [(None,), ("md",), ("rst",)])
def test_command_new_with_readme(fmt, tester, tmp_dir):
    fmt = "md"
    package = "package"
    path = Path(tmp_dir) / package
    options = ["--readme {}".format(fmt) if fmt else "md", path.as_posix()]
    tester.execute(" ".join(options))

    poetry = verify_project_directory(path, package, package, None)
    assert poetry.local_config.get("readme") == "README.{}".format(fmt or "md")
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
