import os
import shutil
import sys

from pathlib import Path

import pytest

from cleo.testers.command_tester import CommandTester

from poetry.repositories import Pool
from poetry.utils._compat import decode
from tests.helpers import TestApplication
from tests.helpers import get_package


@pytest.fixture
def source_dir(tmp_path) -> Path:
    cwd = os.getcwd()

    try:
        os.chdir(str(tmp_path))
        yield Path(tmp_path.as_posix())
    finally:
        os.chdir(cwd)


@pytest.fixture
def patches(mocker, source_dir, repo):
    mocker.patch("pathlib.Path.cwd", return_value=source_dir)
    mocker.patch(
        "poetry.console.commands.init.InitCommand._get_pool", return_value=Pool([repo])
    )


@pytest.fixture
def tester(patches):
    # we need a test application without poetry here.
    app = TestApplication(None)
    return CommandTester(app.find("init"))


@pytest.fixture
def init_basic_inputs():
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
def init_basic_toml():
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


def test_basic_interactive(tester, init_basic_inputs, init_basic_toml):
    tester.execute(inputs=init_basic_inputs)
    assert init_basic_toml in tester.io.fetch_output()


def test_noninteractive(app, mocker, poetry, repo, tmp_path):
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
    assert "" == tester.io.fetch_error()

    toml_content = (tmp_path / "pyproject.toml").read_text()
    assert 'name = "my-package"' in toml_content
    assert 'pytest = "^3.6.0"' in toml_content


def test_interactive_with_dependencies(tester, repo):
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


def test_empty_license(tester):
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

    expected = """\
[tool.poetry]
name = "my-package"
version = "1.2.3"
description = ""
authors = ["Your Name <you@example.com>"]
readme = "README.md"
packages = [{{include = "my_package"}}]

[tool.poetry.dependencies]
python = "^{python}"
""".format(
        python=".".join(str(c) for c in sys.version_info[:2])
    )
    assert expected in tester.io.fetch_output()


def test_interactive_with_git_dependencies(tester, repo):
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


def test_interactive_with_git_dependencies_with_reference(tester, repo):
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


def test_interactive_with_git_dependencies_and_other_name(tester, repo):
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


def test_interactive_with_directory_dependency(tester, repo, source_dir, fixture_dir):
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
    tester, repo, source_dir, fixture_dir
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


def test_interactive_with_file_dependency(tester, repo, source_dir, fixture_dir):
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


def test_python_option(tester):
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


def test_predefined_dependency(tester, repo):
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


def test_predefined_and_interactive_dependencies(tester, repo):
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


def test_predefined_dev_dependency(tester, repo):
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


def test_predefined_and_interactive_dev_dependencies(tester, repo):
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


def test_add_package_with_extras_and_whitespace(tester):
    result = tester.command._parse_requirements(["databases[postgresql, sqlite]"])

    assert result[0]["name"] == "databases"
    assert len(result[0]["extras"]) == 2
    assert "postgresql" in result[0]["extras"]
    assert "sqlite" in result[0]["extras"]


def test_init_existing_pyproject_simple(
    tester, source_dir, init_basic_inputs, init_basic_toml
):
    pyproject_file = source_dir / "pyproject.toml"
    existing_section = """
[tool.black]
line-length = 88
"""
    pyproject_file.write_text(decode(existing_section))
    tester.execute(inputs=init_basic_inputs)
    assert (
        "{}\n{}".format(existing_section, init_basic_toml) in pyproject_file.read_text()
    )


def test_init_non_interactive_existing_pyproject_add_dependency(
    tester, source_dir, init_basic_inputs, repo
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
    assert "{}\n{}".format(existing_section, expected) in pyproject_file.read_text()


def test_init_existing_pyproject_with_build_system_fails(
    tester, source_dir, init_basic_inputs
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
    assert "{}".format(existing_section) in pyproject_file.read_text()
