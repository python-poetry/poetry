import os
import shutil
import sys

from pathlib import Path
<<<<<<< HEAD
from typing import TYPE_CHECKING
from typing import Iterator
=======
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

import pytest

from cleo.testers.command_tester import CommandTester

from poetry.repositories import Pool
from poetry.utils._compat import decode
<<<<<<< HEAD
from tests.helpers import PoetryTestApplication
from tests.helpers import get_package


if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry
    from tests.helpers import TestRepository
    from tests.types import FixtureDirGetter


@pytest.fixture
def source_dir(tmp_path: Path) -> Iterator[Path]:
=======
from tests.helpers import TestApplication
from tests.helpers import get_package


@pytest.fixture
def source_dir(tmp_path) -> Path:
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    cwd = os.getcwd()

    try:
        os.chdir(str(tmp_path))
        yield Path(tmp_path.as_posix())
    finally:
        os.chdir(cwd)


@pytest.fixture
<<<<<<< HEAD
def patches(mocker: "MockerFixture", source_dir: Path, repo: "TestRepository") -> None:
=======
def patches(mocker, source_dir, repo):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    mocker.patch("pathlib.Path.cwd", return_value=source_dir)
    mocker.patch(
        "poetry.console.commands.init.InitCommand._get_pool", return_value=Pool([repo])
    )


@pytest.fixture
<<<<<<< HEAD
def tester(patches: None) -> CommandTester:
    # we need a test application without poetry here.
    app = PoetryTestApplication(None)
=======
def tester(patches):
    # we need a test application without poetry here.
    app = TestApplication(None)
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return CommandTester(app.find("init"))


@pytest.fixture
<<<<<<< HEAD
def init_basic_inputs() -> str:
=======
def init_basic_inputs():
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return "\n".join(
        [
            "my-package",  # Package name
            "1.2.3",  # Version
            "This is a description",  # Description
            "n",  # Author
            "MIT",  # License
            "~2.7 || ^3.6",  # Python
            "n",  # Interactive packages
            "n",  # Interactive dev packages
            "\n",  # Generate
        ]
    )


@pytest.fixture()
<<<<<<< HEAD
def init_basic_toml() -> str:
=======
def init_basic_toml():
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return """\
[tool.poetry]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = ["Your Name <you@example.com>"]
license = "MIT"
readme = "README.md"
packages = [{include = "my_package"}]

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
"""


<<<<<<< HEAD
def test_basic_interactive(
    tester: CommandTester, init_basic_inputs: str, init_basic_toml: str
):
=======
def test_basic_interactive(tester, init_basic_inputs, init_basic_toml):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    tester.execute(inputs=init_basic_inputs)
    assert init_basic_toml in tester.io.fetch_output()


<<<<<<< HEAD
def test_noninteractive(
    app: PoetryTestApplication,
    mocker: "MockerFixture",
    poetry: "Poetry",
    repo: "TestRepository",
    tmp_path: Path,
):
=======
def test_noninteractive(app, mocker, poetry, repo, tmp_path):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    command = app.find("init")
    command._pool = poetry.pool

    repo.add_package(get_package("pytest", "3.6.0"))

    p = mocker.patch("pathlib.Path.cwd")
    p.return_value = tmp_path

    tester = CommandTester(command)
    args = "--name my-package --dependency pytest"
    tester.execute(args=args, interactive=False)

    expected = "Using version ^3.6.0 for pytest\n"
    assert tester.io.fetch_output() == expected
<<<<<<< HEAD
    assert tester.io.fetch_error() == ""
=======
    assert "" == tester.io.fetch_error()
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

    toml_content = (tmp_path / "pyproject.toml").read_text()
    assert 'name = "my-package"' in toml_content
    assert 'pytest = "^3.6.0"' in toml_content


<<<<<<< HEAD
def test_interactive_with_dependencies(tester: CommandTester, repo: "TestRepository"):
=======
def test_interactive_with_dependencies(tester, repo):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    repo.add_package(get_package("django-pendulum", "0.1.6-pre4"))
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))

    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        "~2.7 || ^3.6",  # Python
        "",  # Interactive packages
        "pendulu",  # Search for package
        "1",  # Second option is pendulum
        "",  # Do not set constraint
        "",  # Stop searching for packages
        "",  # Interactive dev packages
        "pytest",  # Search for package
        "0",
        "",
        "",
        "\n",  # Generate
    ]
    tester.execute(inputs="\n".join(inputs))

    expected = """\
[tool.poetry]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = ["Your Name <you@example.com>"]
license = "MIT"
readme = "README.md"
packages = [{include = "my_package"}]

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
pendulum = "^2.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^3.6.0"
"""

    assert expected in tester.io.fetch_output()


<<<<<<< HEAD
def test_empty_license(tester: CommandTester):
=======
def test_empty_license(tester):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "",  # Description
        "n",  # Author
        "",  # License
        "",  # Python
        "n",  # Interactive packages
        "n",  # Interactive dev packages
        "\n",  # Generate
    ]
    tester.execute(inputs="\n".join(inputs))

<<<<<<< HEAD
    python = ".".join(str(c) for c in sys.version_info[:2])
    expected = f"""\
=======
    expected = """\
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
[tool.poetry]
name = "my-package"
version = "1.2.3"
description = ""
authors = ["Your Name <you@example.com>"]
readme = "README.md"
packages = [{{include = "my_package"}}]

[tool.poetry.dependencies]
python = "^{python}"
<<<<<<< HEAD
"""
    assert expected in tester.io.fetch_output()


def test_interactive_with_git_dependencies(
    tester: CommandTester, repo: "TestRepository"
):
=======
""".format(
        python=".".join(str(c) for c in sys.version_info[:2])
    )
    assert expected in tester.io.fetch_output()


def test_interactive_with_git_dependencies(tester, repo):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))

    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        "~2.7 || ^3.6",  # Python
        "",  # Interactive packages
        "git+https://github.com/demo/demo.git",  # Search for package
        "",  # Stop searching for packages
        "",  # Interactive dev packages
        "pytest",  # Search for package
        "0",
        "",
        "",
        "\n",  # Generate
    ]
    tester.execute(inputs="\n".join(inputs))

    expected = """\
[tool.poetry]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = ["Your Name <you@example.com>"]
license = "MIT"
readme = "README.md"
packages = [{include = "my_package"}]

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
demo = {git = "https://github.com/demo/demo.git"}

[tool.poetry.group.dev.dependencies]
pytest = "^3.6.0"
"""

    assert expected in tester.io.fetch_output()


<<<<<<< HEAD
def test_interactive_with_git_dependencies_with_reference(
    tester: CommandTester, repo: "TestRepository"
):
=======
def test_interactive_with_git_dependencies_with_reference(tester, repo):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))

    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        "~2.7 || ^3.6",  # Python
        "",  # Interactive packages
        "git+https://github.com/demo/demo.git@develop",  # Search for package
        "",  # Stop searching for packages
        "",  # Interactive dev packages
        "pytest",  # Search for package
        "0",
        "",
        "",
        "\n",  # Generate
    ]
    tester.execute(inputs="\n".join(inputs))

    expected = """\
[tool.poetry]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = ["Your Name <you@example.com>"]
license = "MIT"
readme = "README.md"
packages = [{include = "my_package"}]

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
demo = {git = "https://github.com/demo/demo.git", rev = "develop"}

[tool.poetry.group.dev.dependencies]
pytest = "^3.6.0"
"""

    assert expected in tester.io.fetch_output()


<<<<<<< HEAD
def test_interactive_with_git_dependencies_and_other_name(
    tester: CommandTester, repo: "TestRepository"
):
=======
def test_interactive_with_git_dependencies_and_other_name(tester, repo):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))

    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        "~2.7 || ^3.6",  # Python
        "",  # Interactive packages
        "git+https://github.com/demo/pyproject-demo.git",  # Search for package
        "",  # Stop searching for packages
        "",  # Interactive dev packages
        "pytest",  # Search for package
        "0",
        "",
        "",
        "\n",  # Generate
    ]
    tester.execute(inputs="\n".join(inputs))

    expected = """\
[tool.poetry]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = ["Your Name <you@example.com>"]
license = "MIT"
readme = "README.md"
packages = [{include = "my_package"}]

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
demo = {git = "https://github.com/demo/pyproject-demo.git"}

[tool.poetry.group.dev.dependencies]
pytest = "^3.6.0"
"""

    assert expected in tester.io.fetch_output()


<<<<<<< HEAD
def test_interactive_with_directory_dependency(
    tester: CommandTester,
    repo: "TestRepository",
    source_dir: Path,
    fixture_dir: "FixtureDirGetter",
):
=======
def test_interactive_with_directory_dependency(tester, repo, source_dir, fixture_dir):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))

    demo = fixture_dir("git") / "github.com" / "demo" / "demo"
    shutil.copytree(str(demo), str(source_dir / "demo"))

    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        "~2.7 || ^3.6",  # Python
        "",  # Interactive packages
        "./demo",  # Search for package
        "",  # Stop searching for packages
        "",  # Interactive dev packages
        "pytest",  # Search for package
        "0",
        "",
        "",
        "\n",  # Generate
    ]
    tester.execute(inputs="\n".join(inputs))

    expected = """\
[tool.poetry]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = ["Your Name <you@example.com>"]
license = "MIT"
readme = "README.md"
packages = [{include = "my_package"}]

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
demo = {path = "demo"}

[tool.poetry.group.dev.dependencies]
pytest = "^3.6.0"
"""
    assert expected in tester.io.fetch_output()


def test_interactive_with_directory_dependency_and_other_name(
<<<<<<< HEAD
    tester: CommandTester,
    repo: "TestRepository",
    source_dir: Path,
    fixture_dir: "FixtureDirGetter",
=======
    tester, repo, source_dir, fixture_dir
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))

    demo = fixture_dir("git") / "github.com" / "demo" / "pyproject-demo"
    shutil.copytree(str(demo), str(source_dir / "pyproject-demo"))

    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        "~2.7 || ^3.6",  # Python
        "",  # Interactive packages
        "./pyproject-demo",  # Search for package
        "",  # Stop searching for packages
        "",  # Interactive dev packages
        "pytest",  # Search for package
        "0",
        "",
        "",
        "\n",  # Generate
    ]
    tester.execute(inputs="\n".join(inputs))

    expected = """\
[tool.poetry]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = ["Your Name <you@example.com>"]
license = "MIT"
readme = "README.md"
packages = [{include = "my_package"}]

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
demo = {path = "pyproject-demo"}

[tool.poetry.group.dev.dependencies]
pytest = "^3.6.0"
"""

    assert expected in tester.io.fetch_output()


<<<<<<< HEAD
def test_interactive_with_file_dependency(
    tester: CommandTester,
    repo: "TestRepository",
    source_dir: Path,
    fixture_dir: "FixtureDirGetter",
):
=======
def test_interactive_with_file_dependency(tester, repo, source_dir, fixture_dir):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))

    demo = fixture_dir("distributions") / "demo-0.1.0-py2.py3-none-any.whl"
    shutil.copyfile(str(demo), str(source_dir / demo.name))

    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        "~2.7 || ^3.6",  # Python
        "",  # Interactive packages
        "./demo-0.1.0-py2.py3-none-any.whl",  # Search for package
        "",  # Stop searching for packages
        "",  # Interactive dev packages
        "pytest",  # Search for package
        "0",
        "",
        "",
        "\n",  # Generate
    ]
    tester.execute(inputs="\n".join(inputs))

    expected = """\
[tool.poetry]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = ["Your Name <you@example.com>"]
license = "MIT"
readme = "README.md"
packages = [{include = "my_package"}]

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
demo = {path = "demo-0.1.0-py2.py3-none-any.whl"}

[tool.poetry.group.dev.dependencies]
pytest = "^3.6.0"
"""

    assert expected in tester.io.fetch_output()


<<<<<<< HEAD
def test_python_option(tester: CommandTester):
=======
def test_python_option(tester):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        "n",  # Interactive packages
        "n",  # Interactive dev packages
        "\n",  # Generate
    ]
    tester.execute("--python '~2.7 || ^3.6'", inputs="\n".join(inputs))

    expected = """\
[tool.poetry]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = ["Your Name <you@example.com>"]
license = "MIT"
readme = "README.md"
packages = [{include = "my_package"}]

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
"""

    assert expected in tester.io.fetch_output()


<<<<<<< HEAD
def test_predefined_dependency(tester: CommandTester, repo: "TestRepository"):
=======
def test_predefined_dependency(tester, repo):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    repo.add_package(get_package("pendulum", "2.0.0"))

    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        "~2.7 || ^3.6",  # Python
        "n",  # Interactive packages
        "n",  # Interactive dev packages
        "\n",  # Generate
    ]
    tester.execute("--dependency pendulum", inputs="\n".join(inputs))

    expected = """\
[tool.poetry]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = ["Your Name <you@example.com>"]
license = "MIT"
readme = "README.md"
packages = [{include = "my_package"}]

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
pendulum = "^2.0.0"
"""

    assert expected in tester.io.fetch_output()


<<<<<<< HEAD
def test_predefined_and_interactive_dependencies(
    tester: CommandTester, repo: "TestRepository"
):
=======
def test_predefined_and_interactive_dependencies(tester, repo):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pyramid", "1.10"))

    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        "~2.7 || ^3.6",  # Python
        "",  # Interactive packages
        "pyramid",  # Search for package
        "0",  # First option
        "",  # Do not set constraint
        "",  # Stop searching for packages
        "n",  # Interactive dev packages
        "\n",  # Generate
    ]

    tester.execute("--dependency pendulum", inputs="\n".join(inputs))

    expected = """\
[tool.poetry]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = ["Your Name <you@example.com>"]
license = "MIT"
readme = "README.md"
packages = [{include = "my_package"}]

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
"""
    output = tester.io.fetch_output()
    assert expected in output
    assert 'pendulum = "^2.0.0"' in output
    assert 'pyramid = "^1.10"' in output


<<<<<<< HEAD
def test_predefined_dev_dependency(tester: CommandTester, repo: "TestRepository"):
=======
def test_predefined_dev_dependency(tester, repo):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    repo.add_package(get_package("pytest", "3.6.0"))

    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        "~2.7 || ^3.6",  # Python
        "n",  # Interactive packages
        "n",  # Interactive dev packages
        "\n",  # Generate
    ]

    tester.execute("--dev-dependency pytest", inputs="\n".join(inputs))

    expected = """\
[tool.poetry]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = ["Your Name <you@example.com>"]
license = "MIT"
readme = "README.md"
packages = [{include = "my_package"}]

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"

[tool.poetry.group.dev.dependencies]
pytest = "^3.6.0"
"""

    assert expected in tester.io.fetch_output()


<<<<<<< HEAD
def test_predefined_and_interactive_dev_dependencies(
    tester: CommandTester, repo: "TestRepository"
):
=======
def test_predefined_and_interactive_dev_dependencies(tester, repo):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    repo.add_package(get_package("pytest", "3.6.0"))
    repo.add_package(get_package("pytest-requests", "0.2.0"))

    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        "~2.7 || ^3.6",  # Python
        "n",  # Interactive packages
        "",  # Interactive dev packages
        "pytest-requests",  # Search for package
        "0",  # Select first option
        "",  # Do not set constraint
        "",  # Stop searching for dev packages
        "\n",  # Generate
    ]

    tester.execute("--dev-dependency pytest", inputs="\n".join(inputs))

    expected = """\
[tool.poetry]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = ["Your Name <you@example.com>"]
license = "MIT"
readme = "README.md"
packages = [{include = "my_package"}]

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"

[tool.poetry.group.dev.dependencies]
pytest = "^3.6.0"
pytest-requests = "^0.2.0"
"""

    output = tester.io.fetch_output()
    assert expected in output
    assert 'pytest-requests = "^0.2.0"' in output
    assert 'pytest = "^3.6.0"' in output


<<<<<<< HEAD
def test_add_package_with_extras_and_whitespace(tester: CommandTester):
=======
def test_add_package_with_extras_and_whitespace(tester):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    result = tester.command._parse_requirements(["databases[postgresql, sqlite]"])

    assert result[0]["name"] == "databases"
    assert len(result[0]["extras"]) == 2
    assert "postgresql" in result[0]["extras"]
    assert "sqlite" in result[0]["extras"]


def test_init_existing_pyproject_simple(
<<<<<<< HEAD
    tester: CommandTester,
    source_dir: Path,
    init_basic_inputs: str,
    init_basic_toml: str,
=======
    tester, source_dir, init_basic_inputs, init_basic_toml
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    pyproject_file = source_dir / "pyproject.toml"
    existing_section = """
[tool.black]
line-length = 88
"""
    pyproject_file.write_text(decode(existing_section))
    tester.execute(inputs=init_basic_inputs)
<<<<<<< HEAD
    assert f"{existing_section}\n{init_basic_toml}" in pyproject_file.read_text()


def test_init_non_interactive_existing_pyproject_add_dependency(
    tester: CommandTester,
    source_dir: Path,
    init_basic_inputs: str,
    repo: "TestRepository",
=======
    assert (
        "{}\n{}".format(existing_section, init_basic_toml) in pyproject_file.read_text()
    )


def test_init_non_interactive_existing_pyproject_add_dependency(
    tester, source_dir, init_basic_inputs, repo
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    pyproject_file = source_dir / "pyproject.toml"
    existing_section = """
[tool.black]
line-length = 88
"""
    pyproject_file.write_text(decode(existing_section))

    repo.add_package(get_package("foo", "1.19.2"))

    tester.execute(
        "--author 'Your Name <you@example.com>' "
        "--name 'my-package' "
        "--python '^3.6' "
        "--dependency foo",
        interactive=False,
    )

    expected = """\
[tool.poetry]
name = "my-package"
version = "0.1.0"
description = ""
authors = ["Your Name <you@example.com>"]
readme = "README.md"
packages = [{include = "my_package"}]

[tool.poetry.dependencies]
python = "^3.6"
foo = "^1.19.2"
"""
<<<<<<< HEAD
    assert f"{existing_section}\n{expected}" in pyproject_file.read_text()


def test_init_existing_pyproject_with_build_system_fails(
    tester: CommandTester, source_dir: Path, init_basic_inputs: str
=======
    assert "{}\n{}".format(existing_section, expected) in pyproject_file.read_text()


def test_init_existing_pyproject_with_build_system_fails(
    tester, source_dir, init_basic_inputs
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    pyproject_file = source_dir / "pyproject.toml"
    existing_section = """
[build-system]
requires = ["setuptools >= 40.6.0", "wheel"]
build-backend = "setuptools.build_meta"
"""
    pyproject_file.write_text(decode(existing_section))
    tester.execute(inputs=init_basic_inputs)
    assert (
        tester.io.fetch_output().strip()
        == "A pyproject.toml file with a defined build-system already exists."
    )
<<<<<<< HEAD
    assert existing_section in pyproject_file.read_text()
=======
    assert "{}".format(existing_section) in pyproject_file.read_text()
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
