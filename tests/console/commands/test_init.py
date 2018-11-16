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
    tester.set_inputs(
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
    tester.execute([("command", command.name)])

    output = tester.get_display(True)
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

    assert expected in output


def test_interactive_with_dependencies(app, repo, mocker, poetry):
    repo.add_package(get_package("pendulum", "2.0.0"))
    repo.add_package(get_package("pytest", "3.6.0"))

    command = app.find("init")
    command._pool = poetry.pool

    mocker.patch("poetry.utils._compat.Path.open")
    p = mocker.patch("poetry.utils._compat.Path.cwd")
    p.return_value = Path(__file__).parent

    tester = CommandTester(command)
    tester.set_inputs(
        [
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
    )
    tester.execute([("command", command.name)])

    output = tester.get_display(True)
    expected = """\
[tool.poetry]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = ["Your Name <you@example.com>"]
license = "MIT"

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
pendulum = "^2.0"

[tool.poetry.dev-dependencies]
pytest = "^3.6"
"""

    assert expected in output


def test_empty_license(app, mocker, poetry):
    command = app.find("init")
    command._pool = poetry.pool

    mocker.patch("poetry.utils._compat.Path.open")
    p = mocker.patch("poetry.utils._compat.Path.cwd")
    p.return_value = Path(__file__)

    tester = CommandTester(command)
    tester.set_inputs(
        [
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
    )
    tester.execute([("command", command.name)])

    output = tester.get_display(True)
    expected = """\
[tool.poetry]
name = "my-package"
version = "1.2.3"
description = ""
authors = ["Your Name <you@example.com>"]

[tool.poetry.dependencies]
python = "^3.7"

[tool.poetry.dev-dependencies]
"""

    assert expected in output
