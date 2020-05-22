import sys

import pytest

from cleo.testers import CommandTester

from poetry.core.semver import Version
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.utils._compat import Path
from tests.helpers import get_dependency
from tests.helpers import get_package


def test_add_no_constraint(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy")

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)
"""

    assert expected == tester.io.fetch_output()

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == "^0.2.0"


def test_add_equal_constraint(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy==0.1.0")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.1.0)
"""

    assert expected == tester.io.fetch_output()

    assert len(installer.installs) == 1


def test_add_greater_constraint(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy>=0.1.0")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)
"""

    assert expected == tester.io.fetch_output()

    assert len(installer.installs) == 1


def test_add_constraint_with_extras(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    cachy1 = get_package("cachy", "0.1.0")
    cachy1.extras = {"msgpack": [get_dependency("msgpack-python")]}
    msgpack_dep = get_dependency("msgpack-python", ">=0.5 <0.6", optional=True)
    cachy1.requires = [msgpack_dep]

    repo.add_package(get_package("cachy", "0.2.0"))
    repo.add_package(cachy1)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    tester.execute("cachy[msgpack]>=0.1.0,<0.2.0")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing msgpack-python (0.5.3)
  - Installing cachy (0.1.0)
"""

    assert expected == tester.io.fetch_output()

    assert len(installer.installs) == 2


def test_add_constraint_dependencies(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    cachy2 = get_package("cachy", "0.2.0")
    msgpack_dep = get_dependency("msgpack-python", ">=0.5 <0.6")
    cachy2.requires = [msgpack_dep]

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    tester.execute("cachy=0.2.0")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing msgpack-python (0.5.3)
  - Installing cachy (0.2.0)
"""

    assert expected == tester.io.fetch_output()

    assert len(installer.installs) == 2


def test_add_git_constraint(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))

    tester.execute("git+https://github.com/demo/demo.git")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.2 9cf87a2)
"""

    assert expected == tester.io.fetch_output()

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

    tester.execute("git+https://github.com/demo/pyproject-demo.git")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.2 9cf87a2)
"""

    assert expected == tester.io.fetch_output()

    assert len(installer.installs) == 2


def test_add_git_constraint_with_extras(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))
    repo.add_package(get_package("tomlkit", "0.5.5"))

    tester.execute("git+https://github.com/demo/demo.git[foo,bar]")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 4 installs, 0 updates, 0 removals

  - Installing cleo (0.6.5)
  - Installing pendulum (1.4.4)
  - Installing tomlkit (0.5.5)
  - Installing demo (0.1.2 9cf87a2)
"""

    assert expected == tester.io.fetch_output()

    assert len(installer.installs) == 4

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "git": "https://github.com/demo/demo.git",
        "extras": ["foo", "bar"],
    }


def test_add_git_ssh_constraint(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))

    tester.execute("git+ssh://git@github.com/demo/demo.git@develop")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.2 9cf87a2)
"""

    assert expected == tester.io.fetch_output()

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "git": "ssh://git@github.com/demo/demo.git",
        "rev": "develop",
    }


def test_add_directory_constraint(app, repo, installer, mocker):
    p = mocker.patch("poetry.utils._compat.Path.cwd")
    p.return_value = Path(__file__) / ".."

    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))

    tester.execute("../git/github.com/demo/demo")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.2 ../git/github.com/demo/demo)
"""

    assert expected == tester.io.fetch_output()

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {"path": "../git/github.com/demo/demo"}


def test_add_directory_with_poetry(app, repo, installer, mocker):
    p = mocker.patch("poetry.utils._compat.Path.cwd")
    p.return_value = Path(__file__) / ".."

    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("pendulum", "1.4.4"))

    tester.execute("../git/github.com/demo/pyproject-demo")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.2 ../git/github.com/demo/pyproject-demo)
"""

    assert expected == tester.io.fetch_output()

    assert len(installer.installs) == 2


def test_add_file_constraint_wheel(app, repo, installer, mocker):
    p = mocker.patch("poetry.utils._compat.Path.cwd")
    p.return_value = Path(__file__) / ".."

    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("pendulum", "1.4.4"))

    tester.execute("../distributions/demo-0.1.0-py2.py3-none-any.whl")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.0 ../distributions/demo-0.1.0-py2.py3-none-any.whl)
"""

    assert expected == tester.io.fetch_output()

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "path": "../distributions/demo-0.1.0-py2.py3-none-any.whl"
    }


def test_add_file_constraint_sdist(app, repo, installer, mocker):
    p = mocker.patch("poetry.utils._compat.Path.cwd")
    p.return_value = Path(__file__) / ".."

    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("pendulum", "1.4.4"))

    tester.execute("../distributions/demo-0.1.0.tar.gz")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.0 ../distributions/demo-0.1.0.tar.gz)
"""

    assert expected == tester.io.fetch_output()

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "path": "../distributions/demo-0.1.0.tar.gz"
    }


def test_add_constraint_with_extras_option(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    cachy2 = get_package("cachy", "0.2.0")
    cachy2.extras = {"msgpack": [get_dependency("msgpack-python")]}
    msgpack_dep = get_dependency("msgpack-python", ">=0.5 <0.6", optional=True)
    cachy2.requires = [msgpack_dep]

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    tester.execute("cachy=0.2.0 --extras msgpack")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing msgpack-python (0.5.3)
  - Installing cachy (0.2.0)
"""

    assert expected == tester.io.fetch_output()

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {
        "version": "0.2.0",
        "extras": ["msgpack"],
    }


def test_add_url_constraint_wheel(app, repo, installer, mocker):
    p = mocker.patch("poetry.utils._compat.Path.cwd")
    p.return_value = Path(__file__) / ".."

    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("pendulum", "1.4.4"))

    tester.execute(
        "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
    )

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.0 https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl)
"""

    assert expected == tester.io.fetch_output()

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "url": "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
    }


def test_add_url_constraint_wheel_with_extras(app, repo, installer, mocker):
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))
    repo.add_package(get_package("tomlkit", "0.5.5"))

    tester.execute(
        "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl[foo,bar]"
    )

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 4 installs, 0 updates, 0 removals

  - Installing cleo (0.6.5)
  - Installing pendulum (1.4.4)
  - Installing tomlkit (0.5.5)
  - Installing demo (0.1.0 https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl)
"""

    assert expected == tester.io.fetch_output()

    assert len(installer.installs) == 4

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "url": "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl",
        "extras": ["foo", "bar"],
    }


def test_add_constraint_with_python(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    cachy2 = get_package("cachy", "0.2.0")

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)

    tester.execute("cachy=0.2.0 --python >=2.7")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)
"""

    assert expected == tester.io.fetch_output()

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {"version": "0.2.0", "python": ">=2.7"}


def test_add_constraint_with_platform(app, repo, installer, env):
    platform = sys.platform
    env._platform = platform
    command = app.find("add")
    tester = CommandTester(command)

    cachy2 = get_package("cachy", "0.2.0")

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)

    tester.execute("cachy=0.2.0 --platform {} -vvv".format(platform))

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)
"""

    assert expected == tester.io.fetch_output()

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {
        "version": "0.2.0",
        "platform": platform,
    }


def test_add_constraint_with_source(app, poetry, installer):
    repo = LegacyRepository(name="my-index", url="https://my-index.fake")
    repo.add_package(get_package("cachy", "0.2.0"))
    repo._cache.store("matches").put("cachy:0.2.0", [Version.parse("0.2.0")], 5)

    poetry.pool.add_repository(repo)

    command = app.find("add")
    tester = CommandTester(command)

    tester.execute("cachy=0.2.0 --source my-index")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)
"""

    assert expected == tester.io.fetch_output()

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {
        "version": "0.2.0",
        "source": "my-index",
    }


def test_add_constraint_with_source_that_does_not_exist(app):
    command = app.find("add")
    tester = CommandTester(command)

    with pytest.raises(ValueError) as e:
        tester.execute("foo --source i-dont-exist")

    assert 'Repository "i-dont-exist" does not exist.' == str(e.value)


def test_add_constraint_not_found_with_source(app, poetry, mocker):
    repo = LegacyRepository(name="my-index", url="https://my-index.fake")
    mocker.patch.object(repo, "find_packages", return_value=[])

    poetry.pool.add_repository(repo)

    pypi = poetry.pool.repositories[0]
    pypi.add_package(get_package("cachy", "0.2.0"))

    command = app.find("add")
    tester = CommandTester(command)

    with pytest.raises(ValueError) as e:
        tester.execute("cachy --source my-index")

    assert "Could not find a matching version of package cachy" == str(e.value)


def test_add_to_section_that_does_no_exist_yet(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy --dev")

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)
"""

    assert expected == tester.io.fetch_output()

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dev-dependencies"]
    assert content["dev-dependencies"]["cachy"] == "^0.2.0"


def test_add_should_not_select_prereleases(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("pyyaml", "3.13"))
    repo.add_package(get_package("pyyaml", "4.2b2"))

    tester.execute("pyyaml")

    expected = """\
Using version ^3.13 for pyyaml

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing pyyaml (3.13)
"""

    assert expected == tester.io.fetch_output()

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "pyyaml" in content["dependencies"]
    assert content["dependencies"]["pyyaml"] == "^3.13"


def test_add_should_display_an_error_when_adding_existing_package_with_no_constraint(
    app, repo, installer
):
    content = app.poetry.file.read()
    content["tool"]["poetry"]["dependencies"]["foo"] = "^1.0"
    app.poetry.file.write(content)
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("foo", "1.1.2"))

    with pytest.raises(ValueError) as e:
        tester.execute("foo")

    assert "Package foo is already present" == str(e.value)


def test_add_should_work_when_adding_existing_package_with_latest_constraint(
    app, repo, installer
):
    content = app.poetry.file.read()
    content["tool"]["poetry"]["dependencies"]["foo"] = "^1.0"
    app.poetry.file.write(content)
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("foo", "1.1.2"))

    tester.execute("foo@latest")

    expected = """\
Using version ^1.1.2 for foo

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing foo (1.1.2)
"""

    assert expected in tester.io.fetch_output()

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "foo" in content["dependencies"]
    assert content["dependencies"]["foo"] == "^1.1.2"


def test_add_chooses_prerelease_if_only_prereleases_are_available(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("foo", "1.2.3b0"))
    repo.add_package(get_package("foo", "1.2.3b1"))

    tester.execute("foo")

    expected = """\
Using version ^1.2.3-beta.1 for foo

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing foo (1.2.3b1)
"""

    assert expected in tester.io.fetch_output()


def test_add_preferes_stable_releases(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("foo", "1.2.3"))
    repo.add_package(get_package("foo", "1.2.4b1"))

    tester.execute("foo")

    expected = """\
Using version ^1.2.3 for foo

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing foo (1.2.3)
"""

    assert expected in tester.io.fetch_output()


def test_add_with_lock(app, repo, installer):
    command = app.find("add")
    tester = CommandTester(command)

    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy --lock")

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...

Writing lock file
"""

    assert expected == tester.io.fetch_output()
