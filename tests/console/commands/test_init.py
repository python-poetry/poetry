from __future__ import annotations

import os
import shutil
import sys
import textwrap

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from cleo.testers.command_tester import CommandTester
from packaging.utils import canonicalize_name
from poetry.core.utils.helpers import module_name

from poetry.console.application import Application
from poetry.console.commands.init import InitCommand
from poetry.repositories import RepositoryPool
from tests.helpers import get_package


if TYPE_CHECKING:
    from collections.abc import Iterator
    from unittest.mock import MagicMock

    from poetry.core.packages.package import Package
    from pytest import FixtureRequest
    from pytest_mock import MockerFixture

    from poetry.config.config import Config
    from poetry.poetry import Poetry
    from tests.helpers import PoetryTestApplication
    from tests.helpers import TestRepository
    from tests.types import FixtureDirGetter
    from tests.types import MockedPythonRegister


@pytest.fixture
def source_dir(tmp_path: Path) -> Iterator[Path]:
    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        yield tmp_path
    finally:
        os.chdir(cwd)


@pytest.fixture
def patches(mocker: MockerFixture, source_dir: Path, repo: TestRepository) -> None:
    mocker.patch("pathlib.Path.cwd", return_value=source_dir)
    mocker.patch(
        "poetry.console.commands.init.InitCommand._get_pool",
        return_value=RepositoryPool([repo]),
    )


@pytest.fixture
def tester(patches: None) -> CommandTester:
    app = Application()
    return CommandTester(app.find("init"))


def test_basic_interactive(
    tester: CommandTester, init_basic_inputs: str, init_basic_toml: str
) -> None:
    tester.execute(inputs=init_basic_inputs)
    assert init_basic_toml in tester.io.fetch_output()


def test_noninteractive(
    app: PoetryTestApplication,
    mocker: MockerFixture,
    poetry: Poetry,
    repo: TestRepository,
    tmp_path: Path,
) -> None:
    command = app.find("init")
    assert isinstance(command, InitCommand)
    command._pool = poetry.pool

    repo.add_package(get_package("pytest", "3.6.0"))

    p = mocker.patch("pathlib.Path.cwd")
    p.return_value = tmp_path

    tester = CommandTester(command)
    args = "--name my-package --dependency pytest"
    tester.execute(args=args, interactive=False)

    expected = "Using version ^3.6.0 for pytest\n"
    assert tester.io.fetch_output() == expected
    assert tester.io.fetch_error() == ""

    toml_content = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "my-package"' in toml_content
    assert '"pytest (>=3.6.0,<4.0.0)"' in toml_content

    expected_build_system = textwrap.dedent("""
    [build-system]
    requires = ["poetry-core>=2.0.0,<3.0.0"]
    build-backend = "poetry.core.masonry.api"
    """)

    assert expected_build_system in toml_content


def test_interactive_with_dependencies(
    tester: CommandTester, repo: TestRepository
) -> None:
    repo.add_package(get_package("django-pendulum", "0.1.6-pre4"))
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))
    repo.add_package(get_package("flask", "2.0.0"))

    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        ">=3.6",  # Python
        "",  # Interactive packages
        "pendulu",  # Search for package
        "1",  # Second option is pendulum
        "",  # Do not set constraint
        "Flask",
        "0",
        "",
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
[project]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = [
    {name = "Your Name",email = "you@example.com"}
]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.6"
dependencies = [
    "pendulum (>=2.0.0,<3.0.0)",
    "flask (>=2.0.0,<3.0.0)"
]

[dependency-groups]
dev = [
    "pytest (>=3.6.0,<4.0.0)"
]


[build-system]
requires = ["poetry-core>=2.0.0,<3.0.0"]
build-backend = "poetry.core.masonry.api"
"""

    assert expected in tester.io.fetch_output()


# Regression test for https://github.com/python-poetry/poetry/issues/2355
def test_interactive_with_dependencies_and_no_selection(
    tester: CommandTester, repo: TestRepository
) -> None:
    repo.add_package(get_package("django-pendulum", "0.1.6-pre4"))
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))

    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        ">=3.6",  # Python
        "",  # Interactive packages
        "pendulu",  # Search for package
        "",  # Do not select an option
        "",  # Stop searching for packages
        "",  # Interactive dev packages
        "pytest",  # Search for package
        "",  # Do not select an option
        "",
        "",
        "\n",  # Generate
    ]
    tester.execute(inputs="\n".join(inputs))
    expected = """\
[project]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = [
    {name = "Your Name",email = "you@example.com"}
]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.6"
"""

    assert expected in tester.io.fetch_output()


def test_empty_license(tester: CommandTester) -> None:
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

    python = ".".join(str(c) for c in sys.version_info[:2])
    expected = f"""\
[project]
name = "my-package"
version = "1.2.3"
description = ""
authors = [
    {{name = "Your Name",email = "you@example.com"}}
]
readme = "README.md"
requires-python = ">={python}"
"""
    assert expected in tester.io.fetch_output()


def test_interactive_with_git_dependencies(
    tester: CommandTester, repo: TestRepository
) -> None:
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))

    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        ">=3.6",  # Python
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
[project]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = [
    {name = "Your Name",email = "you@example.com"}
]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.6"
dependencies = [
    "demo @ git+https://github.com/demo/demo.git"
]

[dependency-groups]
dev = [
    "pytest (>=3.6.0,<4.0.0)"
]
"""

    assert expected in tester.io.fetch_output()


_generate_choice_list_packages_params: list[list[Package]] = [
    [
        get_package("flask-blacklist", "1.0.0"),
        get_package("Flask-Shelve", "1.0.0"),
        get_package("flask-pwa", "1.0.0"),
        get_package("Flask-test1", "1.0.0"),
        get_package("Flask-test2", "1.0.0"),
        get_package("Flask-test3", "1.0.0"),
        get_package("Flask-test4", "1.0.0"),
        get_package("Flask-test5", "1.0.0"),
        get_package("Flask", "1.0.0"),
        get_package("Flask-test6", "1.0.0"),
        get_package("Flask-test7", "1.0.0"),
    ],
    [
        get_package("flask-blacklist", "1.0.0"),
        get_package("Flask-Shelve", "1.0.0"),
        get_package("flask-pwa", "1.0.0"),
        get_package("Flask-test1", "1.0.0"),
        get_package("Flask", "1.0.0"),
    ],
]


@pytest.fixture(params=_generate_choice_list_packages_params)
def _generate_choice_list_packages(request: FixtureRequest) -> list[Package]:
    packages: list[Package] = request.param
    return packages


@pytest.mark.parametrize("package_name", ["flask", "Flask", "flAsK"])
def test_generate_choice_list(
    tester: CommandTester,
    package_name: str,
    _generate_choice_list_packages: list[Package],
) -> None:
    init_command = tester.command
    assert isinstance(init_command, InitCommand)

    packages = _generate_choice_list_packages
    choices = init_command._generate_choice_list(
        packages, canonicalize_name(package_name)
    )

    assert choices[0] == "Flask"


def test_interactive_with_git_dependencies_with_reference(
    tester: CommandTester, repo: TestRepository
) -> None:
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))

    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        ">=3.6",  # Python
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
[project]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = [
    {name = "Your Name",email = "you@example.com"}
]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.6"
dependencies = [
    "demo @ git+https://github.com/demo/demo.git@develop"
]

[dependency-groups]
dev = [
    "pytest (>=3.6.0,<4.0.0)"
]
"""

    assert expected in tester.io.fetch_output()


def test_interactive_with_git_dependencies_and_other_name(
    tester: CommandTester, repo: TestRepository
) -> None:
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))

    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        ">=3.6",  # Python
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
[project]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = [
    {name = "Your Name",email = "you@example.com"}
]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.6"
dependencies = [
    "demo @ git+https://github.com/demo/pyproject-demo.git"
]

[dependency-groups]
dev = [
    "pytest (>=3.6.0,<4.0.0)"
]
"""

    assert expected in tester.io.fetch_output()


def test_interactive_with_directory_dependency(
    tester: CommandTester,
    repo: TestRepository,
    source_dir: Path,
    fixture_dir: FixtureDirGetter,
) -> None:
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
        ">=3.6",  # Python
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

    demo_uri = (Path.cwd() / "demo").as_uri()
    expected = f"""\
[project]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = [
    {{name = "Your Name",email = "you@example.com"}}
]
license = {{text = "MIT"}}
readme = "README.md"
requires-python = ">=3.6"
dependencies = [
    "demo @ {demo_uri}"
]

[dependency-groups]
dev = [
    "pytest (>=3.6.0,<4.0.0)"
]
"""
    assert expected in tester.io.fetch_output()


def test_interactive_with_directory_dependency_and_other_name(
    tester: CommandTester,
    repo: TestRepository,
    source_dir: Path,
    fixture_dir: FixtureDirGetter,
) -> None:
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
        ">=3.6",  # Python
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

    demo_uri = (Path.cwd() / "pyproject-demo").as_uri()
    expected = f"""\
[project]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = [
    {{name = "Your Name",email = "you@example.com"}}
]
license = {{text = "MIT"}}
readme = "README.md"
requires-python = ">=3.6"
dependencies = [
    "demo @ {demo_uri}"
]

[dependency-groups]
dev = [
    "pytest (>=3.6.0,<4.0.0)"
]
"""

    assert expected in tester.io.fetch_output()


def test_interactive_with_file_dependency(
    tester: CommandTester,
    repo: TestRepository,
    source_dir: Path,
    fixture_dir: FixtureDirGetter,
) -> None:
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
        ">=3.6",  # Python
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

    demo_uri = (Path.cwd() / "demo-0.1.0-py2.py3-none-any.whl").as_uri()
    expected = f"""\
[project]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = [
    {{name = "Your Name",email = "you@example.com"}}
]
license = {{text = "MIT"}}
readme = "README.md"
requires-python = ">=3.6"
dependencies = [
    "demo @ {demo_uri}"
]

[dependency-groups]
dev = [
    "pytest (>=3.6.0,<4.0.0)"
]
"""

    assert expected in tester.io.fetch_output()


def test_interactive_with_wrong_dependency_inputs(
    tester: CommandTester, repo: TestRepository
) -> None:
    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        ">=3.8",  # Python
        "",  # Interactive packages
        "foo 1.19.2",
        "pendulum 2.0.0 foo",  # Package name and constraint (invalid)
        "pendulum@^2.0.0",  # Package name and constraint (valid)
        "",  # End package selection
        "",  # Interactive dev packages
        "pytest 3.6.0 foo",  # Dev package name and constraint (invalid)
        "pytest 3.6.0",  # Dev package name and constraint (invalid)
        "pytest@3.6.0",  # Dev package name and constraint (valid)
        "",  # End package selection
        "\n",  # Generate
    ]
    tester.execute(inputs="\n".join(inputs))

    expected = """\
[project]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = [
    {name = "Your Name",email = "you@example.com"}
]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.8"
dependencies = [
    "foo (==1.19.2)",
    "pendulum (>=2.0.0,<3.0.0)"
]

[dependency-groups]
dev = [
    "pytest (==3.6.0)"
]
"""

    assert expected in tester.io.fetch_output()


def test_python_option(tester: CommandTester) -> None:
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
    tester.execute("--python '>=3.6'", inputs="\n".join(inputs))

    expected = """\
[project]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = [
    {name = "Your Name",email = "you@example.com"}
]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.6"
"""

    assert expected in tester.io.fetch_output()


def test_predefined_dependency(tester: CommandTester, repo: TestRepository) -> None:
    repo.add_package(get_package("pendulum", "2.0.0"))

    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        ">=3.6",  # Python
        "n",  # Interactive packages
        "n",  # Interactive dev packages
        "\n",  # Generate
    ]
    tester.execute("--dependency pendulum", inputs="\n".join(inputs))

    expected = """\
[project]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = [
    {name = "Your Name",email = "you@example.com"}
]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.6"
dependencies = [
    "pendulum (>=2.0.0,<3.0.0)"
]
"""

    assert expected in tester.io.fetch_output()


def test_predefined_and_interactive_dependencies(
    tester: CommandTester, repo: TestRepository
) -> None:
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pyramid", "1.10"))

    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        ">=3.6",  # Python
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
[project]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = [
    {name = "Your Name",email = "you@example.com"}
]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.6"
dependencies = [
    "pendulum (>=2.0.0,<3.0.0)",
    "pyramid (>=1.10,<2.0)"
]
"""
    assert expected in tester.io.fetch_output()


def test_predefined_dev_dependency(tester: CommandTester, repo: TestRepository) -> None:
    repo.add_package(get_package("pytest", "3.6.0"))

    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        ">=3.6",  # Python
        "n",  # Interactive packages
        "n",  # Interactive dev packages
        "\n",  # Generate
    ]

    tester.execute("--dev-dependency pytest", inputs="\n".join(inputs))

    expected = """\
[project]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = [
    {name = "Your Name",email = "you@example.com"}
]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.6"
dependencies = [
]

[dependency-groups]
dev = [
    "pytest (>=3.6.0,<4.0.0)"
]
"""

    assert expected in tester.io.fetch_output()


def test_predefined_and_interactive_dev_dependencies(
    tester: CommandTester, repo: TestRepository
) -> None:
    repo.add_package(get_package("pytest", "3.6.0"))
    repo.add_package(get_package("pytest-requests", "0.2.0"))

    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        ">=3.6",  # Python
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
[project]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = [
    {name = "Your Name",email = "you@example.com"}
]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.6"
dependencies = [
]

[dependency-groups]
dev = [
    "pytest (>=3.6.0,<4.0.0)",
    "pytest-requests (>=0.2.0,<0.3.0)"
]
"""

    output = tester.io.fetch_output()
    assert expected in output


def test_predefined_all_options(tester: CommandTester, repo: TestRepository) -> None:
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))

    inputs = [
        "1.2.3",  # Version
        "",  # Author
        "n",  # Interactive packages
        "n",  # Interactive dev packages
        "\n",  # Generate
    ]

    tester.execute(
        "--name my-package "
        "--description 'This is a description' "
        "--author 'Foo Bar <foo@example.com>' "
        "--python '>=3.8' "
        "--license MIT "
        "--dependency pendulum "
        "--dev-dependency pytest",
        inputs="\n".join(inputs),
    )

    expected = """\
[project]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = [
    {name = "Foo Bar",email = "foo@example.com"}
]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.8"
dependencies = [
    "pendulum (>=2.0.0,<3.0.0)"
]

[dependency-groups]
dev = [
    "pytest (>=3.6.0,<4.0.0)"
]
"""

    output = tester.io.fetch_output()
    assert expected in output


def test_add_package_with_extras_and_whitespace(tester: CommandTester) -> None:
    command = tester.command
    assert isinstance(command, InitCommand)
    result = command._parse_requirements(["databases[postgresql, sqlite]"])

    assert result[0]["name"] == "databases"
    assert len(result[0]["extras"]) == 2
    assert "postgresql" in result[0]["extras"]
    assert "sqlite" in result[0]["extras"]


def test_init_existing_pyproject_simple(
    tester: CommandTester,
    source_dir: Path,
    init_basic_inputs: str,
    init_basic_toml: str,
) -> None:
    pyproject_file = source_dir / "pyproject.toml"
    existing_section = """
[tool.black]
line-length = 88
"""
    pyproject_file.write_text(existing_section, encoding="utf-8")
    tester.execute(inputs=init_basic_inputs)
    assert f"{existing_section}\n{init_basic_toml}" in pyproject_file.read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize("linesep", ["\n", "\r\n"])
def test_init_existing_pyproject_consistent_linesep(
    tester: CommandTester,
    source_dir: Path,
    init_basic_inputs: str,
    init_basic_toml: str,
    linesep: str,
) -> None:
    pyproject_file = source_dir / "pyproject.toml"
    existing_section = """
[tool.black]
line-length = 88
""".replace("\n", linesep)
    with open(pyproject_file, "w", newline="", encoding="utf-8") as f:
        f.write(existing_section)
    tester.execute(inputs=init_basic_inputs)
    with open(pyproject_file, newline="", encoding="utf-8") as f:
        content = f.read()
    init_basic_toml = init_basic_toml.replace("\n", linesep)
    assert f"{existing_section}{linesep}{init_basic_toml}" in content


def test_init_non_interactive_existing_pyproject_add_dependency(
    tester: CommandTester,
    source_dir: Path,
    init_basic_inputs: str,
    repo: TestRepository,
) -> None:
    pyproject_file = source_dir / "pyproject.toml"
    existing_section = """
[tool.black]
line-length = 88
"""
    pyproject_file.write_text(existing_section, encoding="utf-8")

    repo.add_package(get_package("foo", "1.19.2"))

    tester.execute(
        "--author 'Your Name <you@example.com>' "
        "--name 'my-package' "
        "--python '>=3.6' "
        "--dependency foo",
        interactive=False,
    )

    expected = """\
[project]
name = "my-package"
version = "0.1.0"
description = ""
authors = [
    {name = "Your Name",email = "you@example.com"}
]
readme = "README.md"
requires-python = ">=3.6"
dependencies = [
    "foo (>=1.19.2,<2.0.0)"
]
"""
    assert f"{existing_section}\n{expected}" in pyproject_file.read_text(
        encoding="utf-8"
    )


def test_init_existing_pyproject_with_build_system_fails(
    tester: CommandTester, source_dir: Path, init_basic_inputs: str
) -> None:
    pyproject_file = source_dir / "pyproject.toml"
    existing_section = """
[build-system]
requires = ["setuptools >= 40.6.0", "wheel"]
build-backend = "setuptools.build_meta"
"""
    pyproject_file.write_text(existing_section, encoding="utf-8")
    tester.execute(inputs=init_basic_inputs)
    assert (
        tester.io.fetch_error().strip()
        == "A pyproject.toml file with a defined build-system already exists."
    )
    assert existing_section in pyproject_file.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "name",
    [
        None,
        "",
        "foo",
        "   foo  ",
        "foo==2.0",
        "foo@2.0",
        "  foo@2.0   ",
        "foo 2.0",
        "   foo 2.0  ",
    ],
)
def test_validate_package_valid(name: str | None) -> None:
    assert InitCommand._validate_package(name) == name


@pytest.mark.parametrize(
    "name", ["foo bar 2.0", "   foo bar 2.0   ", "foo bar foobar 2.0"]
)
def test_validate_package_invalid(name: str) -> None:
    with pytest.raises(ValueError):
        assert InitCommand._validate_package(name)


@pytest.mark.parametrize(
    "author",
    [
        str(b"Jos\x65\xcc\x81 Duarte", "utf-8"),
        str(b"Jos\xc3\xa9 Duarte", "utf-8"),
    ],
)
def test_validate_author(author: str) -> None:
    """
    This test was added following issue #8779, hence, we're looking to see if the test
    no longer throws an exception, hence the seemingly "useless" test of just running
    the method.
    """
    InitCommand._validate_author(author, "")


@pytest.mark.parametrize(
    "package_name, include",
    (
        ("mypackage", None),
        ("my-package", "my_package"),
        ("my.package", "my"),
        ("my-awesome-package", "my_awesome_package"),
        ("my.awesome.package", "my"),
    ),
)
def test_package_include(
    tester: CommandTester,
    package_name: str,
    include: str | None,
) -> None:
    tester.execute(
        inputs="\n".join(
            (
                package_name,
                "",  # Version
                "",  # Description
                "poetry",  # Author
                "",  # License
                ">=3.10",  # Python
                "n",  # Interactive packages
                "n",  # Interactive dev packages
                "\n",  # Generate
            ),
        ),
    )

    packages = ""
    if include and module_name(package_name) != include:
        packages = f'\n[tool.poetry]\npackages = [{{include = "{include}"}}]\n'

    expected = (
        "[project]\n"
        f'name = "{package_name.replace(".", "-")}"\n'  # canonicalized
        'version = "0.1.0"\n'
        'description = ""\n'
        "authors = [\n"
        '    {name = "poetry"}\n'
        "]\n"
        'readme = "README.md"\n'
        'requires-python = ">=3.10"\n'
        "dependencies = [\n"
        "]\n"
        f"{packages}"  # This line is optional. Thus, no newline here.
    )
    assert expected in tester.io.fetch_output()


@pytest.mark.parametrize(
    ["use_poetry_python", "python"],
    [
        (False, "1.1"),
        (True, f"{sys.version_info[0]}.{sys.version_info[1]}"),
    ],
)
def test_respect_use_poetry_python_on_init(
    use_poetry_python: bool,
    python: str,
    config: Config,
    tester: CommandTester,
    source_dir: Path,
    mocked_python_register: MockedPythonRegister,
    with_no_active_python: MagicMock,
) -> None:
    mocked_python_register(f"{python}.1", make_system=True)
    config.config["virtualenvs"]["use-poetry-python"] = use_poetry_python
    pyproject_file = source_dir / "pyproject.toml"

    tester.execute(
        "--author 'Your Name <you@example.com>' --name 'my-package'",
        interactive=False,
    )

    expected = f"""\
requires-python = ">={python}"
"""

    assert expected in pyproject_file.read_text(encoding="utf-8")


def test_get_pool(mocker: MockerFixture, source_dir: Path) -> None:
    """
    Since we are mocking _get_pool() in the other tests, we at least should make
    sure it works in general. See https://github.com/python-poetry/poetry/issues/8634.
    """
    mocker.patch("pathlib.Path.cwd", return_value=source_dir)

    app = Application()
    command = app.find("init")
    assert isinstance(command, InitCommand)
    pool = command._get_pool()
    assert pool.repositories


def test_init_does_not_create_project_structure_in_empty_directory(
    tester: CommandTester, source_dir: Path
) -> None:
    """Test that poetry init does not create project structure in empty directory."""
    inputs = [
        "my-package",  # Package name
        "1.0.0",  # Version
        "",  # Description
        "n",  # Author
        "",  # License
        "",  # Python
        "n",  # Interactive packages
        "n",  # Interactive dev packages
        "\n",  # Generate
    ]

    tester.execute(inputs="\n".join(inputs))

    # Should only create pyproject.toml
    assert (source_dir / "pyproject.toml").exists()

    # Should NOT create these
    assert not (source_dir / "tests").exists()
    assert not (source_dir / "my_package").exists()
    assert not (source_dir / "src").exists()
    assert not (source_dir / "README.md").exists()


def test_init_does_not_create_project_structure_in_non_empty_directory(
    tester: CommandTester, source_dir: Path
) -> None:
    """Test that poetry init does not create project structure in non-empty directory."""
    # Create some existing files
    (source_dir / "existing_file.txt").write_text("existing content", encoding="utf-8")
    (source_dir / "existing_dir").mkdir()

    inputs = [
        "my-package",  # Package name
        "1.0.0",  # Version
        "",  # Description
        "n",  # Author
        "",  # License
        "",  # Python
        "n",  # Interactive packages
        "n",  # Interactive dev packages
        "\n",  # Generate
    ]

    tester.execute(inputs="\n".join(inputs))

    # Should only create pyproject.toml
    assert (source_dir / "pyproject.toml").exists()

    # Should NOT create these
    assert not (source_dir / "tests").exists()
    assert not (source_dir / "my_package").exists()
    assert not (source_dir / "src").exists()
    assert not (source_dir / "README.md").exists()

    # Existing files should remain
    assert (source_dir / "existing_file.txt").exists()
    assert (source_dir / "existing_dir").exists()


def test_init_with_no_package_mode_flag_active(
    tester: CommandTester, source_dir: Path
) -> None:
    """Test that poetry init add package-mode = false to pyproject.toml"""
    inputs = [
        "my-package",  # Package name
        "",  # Version
        "",  # Description
        "n",  # Author
        "",  # License
        "",  # Python
        "n",  # Interactive packages
        "n",  # Interactive dev packages
        "\n",  # Generate
    ]

    expected = """\
[tool.poetry]
package-mode = false
"""
    tester.execute("--disable-package-mode", inputs="\n".join(inputs))

    assert (source_dir / "pyproject.toml").exists()
    assert expected in (source_dir / "pyproject.toml").read_text(encoding="utf-8")


def test_init_with_no_package_mode_flag_active_short_flag(
    tester: CommandTester, source_dir: Path
) -> None:
    """Test that poetry init add package-mode = false to pyproject.toml"""
    inputs = [
        "my-package",  # Package name
        "",  # Version
        "",  # Description
        "n",  # Author
        "",  # License
        "",  # Python
        "n",  # Interactive packages
        "n",  # Interactive dev packages
        "\n",  # Generate
    ]

    expected = """\
[tool.poetry]
package-mode = false
"""
    tester.execute("-N", inputs="\n".join(inputs))

    assert (source_dir / "pyproject.toml").exists()
    assert expected in (source_dir / "pyproject.toml").read_text(encoding="utf-8")


def test_init_with_no_package_mode_flag_active_remove_optional_fields(
    tester: CommandTester, source_dir: Path
) -> None:
    """Test that poetry init add package-mode = false to pyproject.toml"""
    inputs = [
        "my-package",  # Package name
        "",  # Version
        "",  # Description
        "n",  # Author
        "",  # License
        "",  # Python
        "n",  # Interactive packages
        "n",  # Interactive dev packages
        "\n",  # Generate
    ]

    tester.execute("-N", inputs="\n".join(inputs))

    assert (source_dir / "pyproject.toml").exists()
    toml_content = (source_dir / "pyproject.toml").read_text(encoding="utf-8")
    assert "version = " not in toml_content
    assert "description =" not in toml_content
    assert "authors =" not in toml_content


def test_init_with_no_package_mode_flag_active_remove_optional_fields_with_email(
    tester: CommandTester, source_dir: Path
) -> None:
    """Test that poetry init add package-mode = false to pyproject.toml"""
    inputs = [
        "my-package",  # Package name
        "",  # Version
        "",  # Description
        "poetry <poetry@poetry.com>",  # Author
        "",  # License
        "",  # Python
        "n",  # Interactive packages
        "n",  # Interactive dev packages
        "\n",  # Generate
    ]

    tester.execute("-N", inputs="\n".join(inputs))
    expected = """
authors = [
    {name = "poetry",email = "poetry@poetry.com"}
]
"""

    assert (source_dir / "pyproject.toml").exists()
    toml_content = (source_dir / "pyproject.toml").read_text(encoding="utf-8")
    assert expected in toml_content
