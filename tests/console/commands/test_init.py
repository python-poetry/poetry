import sys

from cleo.testers import CommandTester

from poetry.utils._compat import Path
from tests.helpers import get_package


def test_basic_interactive(app, mocker, poetry):
    command = app.find("init")
    command._pool = poetry.pool

    mocker.patch("poetry.utils._compat.Path.open")
    p = mocker.patch("poetry.utils._compat.Path.cwd")
    p.return_value = Path(__file__)

    tester = CommandTester(command)
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
    tester.execute(inputs="\n".join(inputs))

    expected = """\
[tool.poetry]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = ["Your Name <you@example.com>"]
license = "MIT"

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"

[tool.poetry.dev-dependencies]
"""

    assert expected in tester.io.fetch_output()


def test_interactive_with_dependencies(app, repo, mocker, poetry):
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))

    command = app.find("init")
    command._pool = poetry.pool

    mocker.patch("poetry.utils._compat.Path.open")
    p = mocker.patch("poetry.utils._compat.Path.cwd")
    p.return_value = Path(__file__).parent

    tester = CommandTester(command)
    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        "~2.7 || ^3.6",  # Python
        "",  # Interactive packages
        "pendulum",  # Search for package
        "0",  # First option
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

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
pendulum = "^2.0.0"

[tool.poetry.dev-dependencies]
pytest = "^3.6.0"
"""

    assert expected in tester.io.fetch_output()


def test_empty_license(app, mocker, poetry):
    command = app.find("init")
    command._pool = poetry.pool

    mocker.patch("poetry.utils._compat.Path.open")
    p = mocker.patch("poetry.utils._compat.Path.cwd")
    p.return_value = Path(__file__)

    tester = CommandTester(command)
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

[tool.poetry.dependencies]
python = "^{python}"

[tool.poetry.dev-dependencies]
""".format(
        python=".".join(str(c) for c in sys.version_info[:2])
    )

    assert expected in tester.io.fetch_output()


def test_interactive_with_git_dependencies(app, repo, mocker, poetry):
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))

    command = app.find("init")
    command._pool = poetry.pool

    mocker.patch("poetry.utils._compat.Path.open")
    p = mocker.patch("poetry.utils._compat.Path.cwd")
    p.return_value = Path(__file__).parent

    tester = CommandTester(command)
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

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
demo = {git = "https://github.com/demo/demo.git"}

[tool.poetry.dev-dependencies]
pytest = "^3.6.0"
"""

    assert expected in tester.io.fetch_output()


def test_interactive_with_git_dependencies_with_reference(app, repo, mocker, poetry):
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))

    command = app.find("init")
    command._pool = poetry.pool

    mocker.patch("poetry.utils._compat.Path.open")
    p = mocker.patch("poetry.utils._compat.Path.cwd")
    p.return_value = Path(__file__).parent

    tester = CommandTester(command)
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

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
demo = {git = "https://github.com/demo/demo.git", rev = "develop"}

[tool.poetry.dev-dependencies]
pytest = "^3.6.0"
"""

    assert expected in tester.io.fetch_output()


def test_interactive_with_git_dependencies_and_other_name(app, repo, mocker, poetry):
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))

    command = app.find("init")
    command._pool = poetry.pool

    mocker.patch("poetry.utils._compat.Path.open")
    p = mocker.patch("poetry.utils._compat.Path.cwd")
    p.return_value = Path(__file__).parent

    tester = CommandTester(command)
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

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
demo = {git = "https://github.com/demo/pyproject-demo.git"}

[tool.poetry.dev-dependencies]
pytest = "^3.6.0"
"""

    assert expected in tester.io.fetch_output()


def test_interactive_with_directory_dependency(app, repo, mocker, poetry):
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))

    command = app.find("init")
    command._pool = poetry.pool

    mocker.patch("poetry.utils._compat.Path.open")
    p = mocker.patch("poetry.utils._compat.Path.cwd")
    p.return_value = Path(__file__).parent

    tester = CommandTester(command)
    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        "~2.7 || ^3.6",  # Python
        "",  # Interactive packages
        "../../fixtures/git/github.com/demo/demo",  # Search for package
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

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
demo = {path = "../../fixtures/git/github.com/demo/demo"}

[tool.poetry.dev-dependencies]
pytest = "^3.6.0"
"""

    assert expected in tester.io.fetch_output()


def test_interactive_with_directory_dependency_and_other_name(
    app, repo, mocker, poetry
):
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))

    command = app.find("init")
    command._pool = poetry.pool

    mocker.patch("poetry.utils._compat.Path.open")
    p = mocker.patch("poetry.utils._compat.Path.cwd")
    p.return_value = Path(__file__).parent

    tester = CommandTester(command)
    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        "~2.7 || ^3.6",  # Python
        "",  # Interactive packages
        "../../fixtures/git/github.com/demo/pyproject-demo",  # Search for package
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

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
demo = {path = "../../fixtures/git/github.com/demo/pyproject-demo"}

[tool.poetry.dev-dependencies]
pytest = "^3.6.0"
"""

    assert expected in tester.io.fetch_output()


def test_interactive_with_file_dependency(app, repo, mocker, poetry):
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))

    command = app.find("init")
    command._pool = poetry.pool

    mocker.patch("poetry.utils._compat.Path.open")
    p = mocker.patch("poetry.utils._compat.Path.cwd")
    p.return_value = Path(__file__).parent

    tester = CommandTester(command)
    inputs = [
        "my-package",  # Package name
        "1.2.3",  # Version
        "This is a description",  # Description
        "n",  # Author
        "MIT",  # License
        "~2.7 || ^3.6",  # Python
        "",  # Interactive packages
        "../../fixtures/distributions/demo-0.1.0-py2.py3-none-any.whl",  # Search for package
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

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
demo = {path = "../../fixtures/distributions/demo-0.1.0-py2.py3-none-any.whl"}

[tool.poetry.dev-dependencies]
pytest = "^3.6.0"
"""

    assert expected in tester.io.fetch_output()
