import sys

from cleo.testers import CommandTester

from tests.helpers import get_dependency
from tests.helpers import get_package


def test_add_no_constraint(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute([("command", command.get_name()), ("name", ["cachy"])])

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...


Package operations: 1 install, 0 updates, 0 removals

Writing lock file

  - Installing cachy (0.2.0)
"""

    assert tester.get_display(True) == expected

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == "^0.2.0"


def test_add_constraint(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute([("command", command.get_name()), ("name", ["cachy=0.1.0"])])

    expected = """\

Updating dependencies
Resolving dependencies...


Package operations: 1 install, 0 updates, 0 removals

Writing lock file

  - Installing cachy (0.1.0)
"""

    assert tester.get_display(True) == expected

    assert len(installer.installs) == 1


def test_add_constraint_dependencies(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    cachy2 = get_package("cachy", "0.2.0")
    msgpack_dep = get_dependency("msgpack-python", ">=0.5 <0.6")
    cachy2.requires = [msgpack_dep]

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    tester.execute([("command", command.get_name()), ("name", ["cachy=0.2.0"])])

    expected = """\

Updating dependencies
Resolving dependencies...


Package operations: 2 installs, 0 updates, 0 removals

Writing lock file

  - Installing msgpack-python (0.5.3)
  - Installing cachy (0.2.0)
"""

    assert tester.get_display(True) == expected

    assert len(installer.installs) == 2


def test_add_git_constraint(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))

    tester.execute(
        [
            ("command", command.get_name()),
            ("name", ["demo"]),
            ("--git", "https://github.com/demo/demo.git"),
        ]
    )

    expected = """\

Updating dependencies
Resolving dependencies...


Package operations: 2 installs, 0 updates, 0 removals

Writing lock file

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.2 9cf87a2)
"""

    assert tester.get_display(True) == expected

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "git": "https://github.com/demo/demo.git"
    }


def test_add_git_constraint_with_poetry(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("pendulum", "1.4.4"))

    tester.execute(
        [
            ("command", command.get_name()),
            ("name", ["demo"]),
            ("--git", "https://github.com/demo/pyproject-demo.git"),
        ]
    )

    expected = """\

Updating dependencies
Resolving dependencies...


Package operations: 2 installs, 0 updates, 0 removals

Writing lock file

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.2 9cf87a2)
"""

    assert tester.get_display(True) == expected

    assert len(installer.installs) == 2


def test_add_file_constraint_wheel(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("pendulum", "1.4.4"))

    tester.execute(
        [
            ("command", command.get_name()),
            ("name", ["demo"]),
            ("--path", "../distributions/demo-0.1.0-py2.py3-none-any.whl"),
        ]
    )

    expected = """\

Updating dependencies
Resolving dependencies...


Package operations: 2 installs, 0 updates, 0 removals

Writing lock file

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.0 ../distributions/demo-0.1.0-py2.py3-none-any.whl)
"""

    assert tester.get_display(True) == expected

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "path": "../distributions/demo-0.1.0-py2.py3-none-any.whl"
    }


def test_add_file_constraint_sdist(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("pendulum", "1.4.4"))

    tester.execute(
        [
            ("command", command.get_name()),
            ("name", ["demo"]),
            ("--path", "../distributions/demo-0.1.0.tar.gz"),
        ]
    )

    expected = """\

Updating dependencies
Resolving dependencies...


Package operations: 2 installs, 0 updates, 0 removals

Writing lock file

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.0 ../distributions/demo-0.1.0.tar.gz)
"""

    assert tester.get_display(True) == expected

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "path": "../distributions/demo-0.1.0.tar.gz"
    }


def test_add_constraint_with_extras(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    cachy2 = get_package("cachy", "0.2.0")
    cachy2.extras = {"msgpack": [get_dependency("msgpack-python")]}
    msgpack_dep = get_dependency("msgpack-python", ">=0.5 <0.6", optional=True)
    cachy2.requires = [msgpack_dep]

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    tester.execute(
        [
            ("command", command.get_name()),
            ("name", ["cachy=0.2.0"]),
            ("--extras", ["msgpack"]),
        ]
    )

    expected = """\

Updating dependencies
Resolving dependencies...


Package operations: 2 installs, 0 updates, 0 removals

Writing lock file

  - Installing msgpack-python (0.5.3)
  - Installing cachy (0.2.0)
"""

    assert tester.get_display(True) == expected

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {
        "version": "0.2.0",
        "extras": ["msgpack"],
    }


def test_add_constraint_with_python(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    cachy2 = get_package("cachy", "0.2.0")

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)

    tester.execute(
        [
            ("command", command.get_name()),
            ("name", ["cachy=0.2.0"]),
            ("--python", ">=2.7"),
        ]
    )

    expected = """\

Updating dependencies
Resolving dependencies...


Package operations: 1 install, 0 updates, 0 removals

Writing lock file

  - Installing cachy (0.2.0)
"""

    assert tester.get_display(True) == expected

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {"version": "0.2.0", "python": ">=2.7"}


def test_add_constraint_with_platform(app, repo, installer):
    platform = sys.platform
    command = app.find("add")
    tester = CommandTester(command)

    cachy2 = get_package("cachy", "0.2.0")

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)

    tester.execute(
        [
            ("command", command.get_name()),
            ("name", ["cachy=0.2.0"]),
            ("--platform", platform),
        ]
    )

    expected = """\

Updating dependencies
Resolving dependencies...


Package operations: 1 install, 0 updates, 0 removals

Writing lock file

  - Installing cachy (0.2.0)
"""

    assert tester.get_display(True) == expected

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {
        "version": "0.2.0",
        "platform": platform,
    }


def test_add_to_section_that_does_no_exist_yet(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute(
        [("command", command.get_name()), ("name", ["cachy"]), ("--dev", True)]
    )

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...


Package operations: 1 install, 0 updates, 0 removals

Writing lock file

  - Installing cachy (0.2.0)
"""

    assert tester.get_display(True) == expected

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dev-dependencies"]
    assert content["dev-dependencies"]["cachy"] == "^0.2.0"


def test_add_should_not_select_prereleases(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("pyyaml", "3.13"))
    repo.add_package(get_package("pyyaml", "4.2b2"))

    tester.execute([("command", command.get_name()), ("name", ["pyyaml"])])

    expected = """\
Using version ^3.13 for pyyaml

Updating dependencies
Resolving dependencies...


Package operations: 1 install, 0 updates, 0 removals

Writing lock file

  - Installing pyyaml (3.13)
"""

    assert tester.get_display(True) == expected

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "pyyaml" in content["dependencies"]
    assert content["dependencies"]["pyyaml"] == "^3.13"
