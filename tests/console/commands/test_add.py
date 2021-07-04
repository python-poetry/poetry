import sys

from pathlib import Path

import pytest

from poetry.core.semver.version import Version
from poetry.repositories.legacy_repository import LegacyRepository
from tests.helpers import get_dependency
from tests.helpers import get_package


@pytest.fixture()
def tester(command_tester_factory):
    return command_tester_factory("add")


@pytest.fixture()
def old_tester(tester):
    tester.command.installer.use_executor(False)

    return tester


def test_add_no_constraint(app, repo, tester):
    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy")

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing cachy (0.2.0)
"""

    assert expected == tester.io.fetch_output()
    assert 1 == tester.command.installer.executor.installations_count

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == "^0.2.0"


def test_add_no_constraint_editable_error(app, repo, tester):
    content = app.poetry.file.read()["tool"]["poetry"]

    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("-e cachy")

    expected = """
Failed to add packages. Only vcs/path dependencies support editable installs. cachy is neither.

No changes were applied.
"""
    assert 1 == tester.status_code
    assert expected == tester.io.fetch_error()
    assert 0 == tester.command.installer.executor.installations_count
    assert content == app.poetry.file.read()["tool"]["poetry"]


def test_add_equal_constraint(app, repo, tester):
    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy==0.1.0")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing cachy (0.1.0)
"""

    assert expected == tester.io.fetch_output()
    assert 1 == tester.command.installer.executor.installations_count


def test_add_greater_constraint(app, repo, tester):
    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy>=0.1.0")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing cachy (0.2.0)
"""

    assert expected == tester.io.fetch_output()
    assert 1 == tester.command.installer.executor.installations_count


def test_add_constraint_with_extras(app, repo, tester):
    cachy1 = get_package("cachy", "0.1.0")
    cachy1.extras = {"msgpack": [get_dependency("msgpack-python")]}
    msgpack_dep = get_dependency("msgpack-python", ">=0.5 <0.6", optional=True)
    cachy1.add_dependency(msgpack_dep)

    repo.add_package(get_package("cachy", "0.2.0"))
    repo.add_package(cachy1)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    tester.execute("cachy[msgpack]>=0.1.0,<0.2.0")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  • Installing msgpack-python (0.5.3)
  • Installing cachy (0.1.0)
"""

    assert expected == tester.io.fetch_output()
    assert 2 == tester.command.installer.executor.installations_count


def test_add_constraint_dependencies(app, repo, tester):
    cachy2 = get_package("cachy", "0.2.0")
    msgpack_dep = get_dependency("msgpack-python", ">=0.5 <0.6")
    cachy2.add_dependency(msgpack_dep)

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    tester.execute("cachy=0.2.0")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  • Installing msgpack-python (0.5.3)
  • Installing cachy (0.2.0)
"""

    assert expected == tester.io.fetch_output()
    assert 2 == tester.command.installer.executor.installations_count


def test_add_git_constraint(app, repo, tester, tmp_venv):
    tester.command.set_env(tmp_venv)

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))

    tester.execute("git+https://github.com/demo/demo.git")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  • Installing pendulum (1.4.4)
  • Installing demo (0.1.2 9cf87a2)
"""

    assert expected == tester.io.fetch_output()
    assert 2 == tester.command.installer.executor.installations_count

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "git": "https://github.com/demo/demo.git"
    }


def test_add_git_constraint_with_poetry(app, repo, tester, tmp_venv):
    tester.command.set_env(tmp_venv)

    repo.add_package(get_package("pendulum", "1.4.4"))

    tester.execute("git+https://github.com/demo/pyproject-demo.git")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  • Installing pendulum (1.4.4)
  • Installing demo (0.1.2 9cf87a2)
"""

    assert expected == tester.io.fetch_output()
    assert 2 == tester.command.installer.executor.installations_count


def test_add_git_constraint_with_extras(app, repo, tester, tmp_venv):
    tester.command.set_env(tmp_venv)

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))
    repo.add_package(get_package("tomlkit", "0.5.5"))

    tester.execute("git+https://github.com/demo/demo.git[foo,bar]")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 4 installs, 0 updates, 0 removals

  • Installing cleo (0.6.5)
  • Installing pendulum (1.4.4)
  • Installing tomlkit (0.5.5)
  • Installing demo (0.1.2 9cf87a2)
"""

    assert expected.strip() == tester.io.fetch_output().strip()
    assert 4 == tester.command.installer.executor.installations_count

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "git": "https://github.com/demo/demo.git",
        "extras": ["foo", "bar"],
    }


@pytest.mark.parametrize("editable", [False, True])
def test_add_git_ssh_constraint(editable, app, repo, tester, tmp_venv):
    tester.command.set_env(tmp_venv)

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))

    url = "git+ssh://git@github.com/demo/demo.git@develop"
    tester.execute(f"{url}" if not editable else f"-e {url}")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  • Installing pendulum (1.4.4)
  • Installing demo (0.1.2 9cf87a2)
"""

    assert expected == tester.io.fetch_output()
    assert 2 == tester.command.installer.executor.installations_count

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]

    expected = {
        "git": "ssh://git@github.com/demo/demo.git",
        "rev": "develop",
    }
    if editable:
        expected["develop"] = True

    assert content["dependencies"]["demo"] == expected


@pytest.mark.parametrize("editable", [False, True])
def test_add_directory_constraint(editable, app, repo, tester, mocker):
    p = mocker.patch("pathlib.Path.cwd")
    p.return_value = Path(__file__).parent

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))

    path = "../git/github.com/demo/demo"
    tester.execute(f"{path}" if not editable else f"-e {path}")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  • Installing pendulum (1.4.4)
  • Installing demo (0.1.2 {})
""".format(
        app.poetry.file.parent.joinpath(path).resolve().as_posix()
    )

    assert expected == tester.io.fetch_output()
    assert 2 == tester.command.installer.executor.installations_count

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]

    expected = {"path": "../git/github.com/demo/demo"}
    if editable:
        expected["develop"] = True

    assert content["dependencies"]["demo"] == expected


def test_add_directory_with_poetry(app, repo, tester, mocker):
    p = mocker.patch("pathlib.Path.cwd")
    p.return_value = Path(__file__) / ".."

    repo.add_package(get_package("pendulum", "1.4.4"))

    path = "../git/github.com/demo/pyproject-demo"
    tester.execute("{}".format(path))

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  • Installing pendulum (1.4.4)
  • Installing demo (0.1.2 {})
""".format(
        app.poetry.file.parent.joinpath(path).resolve().as_posix()
    )

    assert expected == tester.io.fetch_output()
    assert 2 == tester.command.installer.executor.installations_count


def test_add_file_constraint_wheel(app, repo, tester, mocker, poetry):
    p = mocker.patch("pathlib.Path.cwd")
    p.return_value = poetry.file.parent

    repo.add_package(get_package("pendulum", "1.4.4"))

    path = "../distributions/demo-0.1.0-py2.py3-none-any.whl"
    tester.execute("{}".format(path))

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  • Installing pendulum (1.4.4)
  • Installing demo (0.1.0 {})
""".format(
        app.poetry.file.parent.joinpath(path).resolve().as_posix()
    )

    assert expected == tester.io.fetch_output()
    assert 2 == tester.command.installer.executor.installations_count

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "path": "../distributions/demo-0.1.0-py2.py3-none-any.whl"
    }


def test_add_file_constraint_sdist(app, repo, tester, mocker):
    p = mocker.patch("pathlib.Path.cwd")
    p.return_value = Path(__file__) / ".."

    repo.add_package(get_package("pendulum", "1.4.4"))

    path = "../distributions/demo-0.1.0.tar.gz"
    tester.execute("{}".format(path))

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  • Installing pendulum (1.4.4)
  • Installing demo (0.1.0 {})
""".format(
        app.poetry.file.parent.joinpath(path).resolve().as_posix()
    )

    assert expected == tester.io.fetch_output()
    assert 2 == tester.command.installer.executor.installations_count

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "path": "../distributions/demo-0.1.0.tar.gz"
    }


def test_add_constraint_with_extras_option(app, repo, tester):
    cachy2 = get_package("cachy", "0.2.0")
    cachy2.extras = {"msgpack": [get_dependency("msgpack-python")]}
    msgpack_dep = get_dependency("msgpack-python", ">=0.5 <0.6", optional=True)
    cachy2.add_dependency(msgpack_dep)

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    tester.execute("cachy=0.2.0 --extras msgpack")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  • Installing msgpack-python (0.5.3)
  • Installing cachy (0.2.0)
"""

    assert expected == tester.io.fetch_output()
    assert 2 == tester.command.installer.executor.installations_count

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {
        "version": "0.2.0",
        "extras": ["msgpack"],
    }


def test_add_url_constraint_wheel(app, repo, tester, mocker):
    p = mocker.patch("pathlib.Path.cwd")
    p.return_value = Path(__file__) / ".."

    repo.add_package(get_package("pendulum", "1.4.4"))

    tester.execute(
        "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
    )

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  • Installing pendulum (1.4.4)
  • Installing demo (0.1.0 https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl)
"""

    assert expected == tester.io.fetch_output()
    assert 2 == tester.command.installer.executor.installations_count

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "url": "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
    }


def test_add_url_constraint_wheel_with_extras(app, repo, tester, mocker):
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

  • Installing cleo (0.6.5)
  • Installing pendulum (1.4.4)
  • Installing tomlkit (0.5.5)
  • Installing demo (0.1.0 https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl)
"""
    # Order might be different, split into lines and compare the overall output.
    expected = set(expected.splitlines())
    output = set(tester.io.fetch_output().splitlines())
    assert expected == output
    assert 4 == tester.command.installer.executor.installations_count

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "url": "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl",
        "extras": ["foo", "bar"],
    }


def test_add_constraint_with_python(app, repo, tester):
    cachy2 = get_package("cachy", "0.2.0")

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)

    tester.execute("cachy=0.2.0 --python >=2.7")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing cachy (0.2.0)
"""

    assert expected == tester.io.fetch_output()
    assert 1 == tester.command.installer.executor.installations_count

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {"version": "0.2.0", "python": ">=2.7"}


def test_add_constraint_with_platform(app, repo, tester, env):
    platform = sys.platform
    env._platform = platform

    cachy2 = get_package("cachy", "0.2.0")

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)

    tester.execute("cachy=0.2.0 --platform {} -vvv".format(platform))

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing cachy (0.2.0)
"""

    assert expected == tester.io.fetch_output()
    assert 1 == tester.command.installer.executor.installations_count

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {
        "version": "0.2.0",
        "platform": platform,
    }


def test_add_constraint_with_source(app, poetry, tester):
    repo = LegacyRepository(name="my-index", url="https://my-index.fake")
    repo.add_package(get_package("cachy", "0.2.0"))
    repo._cache.store("matches").put("cachy:0.2.0", [Version.parse("0.2.0")], 5)

    poetry.pool.add_repository(repo)

    tester.execute("cachy=0.2.0 --source my-index")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing cachy (0.2.0)
"""

    assert expected == tester.io.fetch_output()
    assert 1 == tester.command.installer.executor.installations_count

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {
        "version": "0.2.0",
        "source": "my-index",
    }


def test_add_constraint_with_source_that_does_not_exist(app, tester):
    with pytest.raises(ValueError) as e:
        tester.execute("foo --source i-dont-exist")

    assert 'Repository "i-dont-exist" does not exist.' == str(e.value)


def test_add_constraint_not_found_with_source(app, poetry, mocker, tester):
    repo = LegacyRepository(name="my-index", url="https://my-index.fake")
    mocker.patch.object(repo, "find_packages", return_value=[])

    poetry.pool.add_repository(repo)

    pypi = poetry.pool.repositories[0]
    pypi.add_package(get_package("cachy", "0.2.0"))

    with pytest.raises(ValueError) as e:
        tester.execute("cachy --source my-index")

    assert "Could not find a matching version of package cachy" == str(e.value)


def test_add_to_section_that_does_not_exist_yet(app, repo, tester):
    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy --group dev")

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing cachy (0.2.0)
"""

    assert expected == tester.io.fetch_output()
    assert 1 == tester.command.installer.executor.installations_count

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["group"]["dev"]["dependencies"]
    assert content["group"]["dev"]["dependencies"]["cachy"] == "^0.2.0"

    expected = """\

[tool.poetry.group.dev.dependencies]
cachy = "^0.2.0"

"""

    assert expected in content.as_string()


def test_add_to_dev_section_deprecated(app, repo, tester):
    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy --dev")

    expected = """\
The --dev option is deprecated, use the `--group dev` notation instead.

Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing cachy (0.2.0)
"""

    assert expected == tester.io.fetch_output()
    assert 1 == tester.command.installer.executor.installations_count

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["group"]["dev"]["dependencies"]
    assert content["group"]["dev"]["dependencies"]["cachy"] == "^0.2.0"


def test_add_should_not_select_prereleases(app, repo, tester):
    repo.add_package(get_package("pyyaml", "3.13"))
    repo.add_package(get_package("pyyaml", "4.2b2"))

    tester.execute("pyyaml")

    expected = """\
Using version ^3.13 for pyyaml

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing pyyaml (3.13)
"""

    assert expected == tester.io.fetch_output()
    assert 1 == tester.command.installer.executor.installations_count

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "pyyaml" in content["dependencies"]
    assert content["dependencies"]["pyyaml"] == "^3.13"


def test_add_should_skip_when_adding_existing_package_with_no_constraint(
    app, repo, tester
):
    content = app.poetry.file.read()
    content["tool"]["poetry"]["dependencies"]["foo"] = "^1.0"
    app.poetry.file.write(content)

    repo.add_package(get_package("foo", "1.1.2"))
    tester.execute("foo")

    expected = """\
The following packages are already present in the pyproject.toml and will be skipped:

  • foo

If you want to update it to the latest compatible version, you can use `poetry update package`.
If you prefer to upgrade it to the latest available version, you can use `poetry add package@latest`.
"""

    assert expected in tester.io.fetch_output()


def test_add_should_work_when_adding_existing_package_with_latest_constraint(
    app, repo, tester
):
    content = app.poetry.file.read()
    content["tool"]["poetry"]["dependencies"]["foo"] = "^1.0"
    app.poetry.file.write(content)

    repo.add_package(get_package("foo", "1.1.2"))

    tester.execute("foo@latest")

    expected = """\
Using version ^1.1.2 for foo

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing foo (1.1.2)
"""

    assert expected in tester.io.fetch_output()

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "foo" in content["dependencies"]
    assert content["dependencies"]["foo"] == "^1.1.2"


def test_add_chooses_prerelease_if_only_prereleases_are_available(app, repo, tester):
    repo.add_package(get_package("foo", "1.2.3b0"))
    repo.add_package(get_package("foo", "1.2.3b1"))

    tester.execute("foo")

    expected = """\
Using version ^1.2.3-beta.1 for foo

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing foo (1.2.3b1)
"""

    assert expected in tester.io.fetch_output()


def test_add_prefers_stable_releases(app, repo, tester):
    repo.add_package(get_package("foo", "1.2.3"))
    repo.add_package(get_package("foo", "1.2.4b1"))

    tester.execute("foo")

    expected = """\
Using version ^1.2.3 for foo

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing foo (1.2.3)
"""

    assert expected in tester.io.fetch_output()


def test_add_with_lock(app, repo, tester):
    content_hash = app.poetry.locker._get_content_hash()
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy --lock")

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...

Writing lock file
"""

    assert expected == tester.io.fetch_output()
    assert content_hash != app.poetry.locker.lock_data["metadata"]["content-hash"]


def test_add_no_constraint_old_installer(app, repo, installer, old_tester):
    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    old_tester.execute("cachy")

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)
"""

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == "^0.2.0"


def test_add_equal_constraint_old_installer(app, repo, installer, old_tester):
    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    old_tester.execute("cachy==0.1.0")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.1.0)
"""

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 1


def test_add_greater_constraint_old_installer(app, repo, installer, old_tester):
    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    old_tester.execute("cachy>=0.1.0")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)
"""

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 1


def test_add_constraint_with_extras_old_installer(app, repo, installer, old_tester):
    cachy1 = get_package("cachy", "0.1.0")
    cachy1.extras = {"msgpack": [get_dependency("msgpack-python")]}
    msgpack_dep = get_dependency("msgpack-python", ">=0.5 <0.6", optional=True)
    cachy1.add_dependency(msgpack_dep)

    repo.add_package(get_package("cachy", "0.2.0"))
    repo.add_package(cachy1)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    old_tester.execute("cachy[msgpack]>=0.1.0,<0.2.0")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing msgpack-python (0.5.3)
  - Installing cachy (0.1.0)
"""

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 2


def test_add_constraint_dependencies_old_installer(app, repo, installer, old_tester):
    cachy2 = get_package("cachy", "0.2.0")
    msgpack_dep = get_dependency("msgpack-python", ">=0.5 <0.6")
    cachy2.add_dependency(msgpack_dep)

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    old_tester.execute("cachy=0.2.0")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing msgpack-python (0.5.3)
  - Installing cachy (0.2.0)
"""

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 2


def test_add_git_constraint_old_installer(app, repo, installer, old_tester):
    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))

    old_tester.execute("git+https://github.com/demo/demo.git")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.2 9cf87a2)
"""

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "git": "https://github.com/demo/demo.git"
    }


def test_add_git_constraint_with_poetry_old_installer(app, repo, installer, old_tester):
    repo.add_package(get_package("pendulum", "1.4.4"))

    old_tester.execute("git+https://github.com/demo/pyproject-demo.git")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.2 9cf87a2)
"""

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 2


def test_add_git_constraint_with_extras_old_installer(app, repo, installer, old_tester):
    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))
    repo.add_package(get_package("tomlkit", "0.5.5"))

    old_tester.execute("git+https://github.com/demo/demo.git[foo,bar]")

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

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 4

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "git": "https://github.com/demo/demo.git",
        "extras": ["foo", "bar"],
    }


def test_add_git_ssh_constraint_old_installer(app, repo, installer, old_tester):
    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))

    old_tester.execute("git+ssh://git@github.com/demo/demo.git@develop")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.2 9cf87a2)
"""

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "git": "ssh://git@github.com/demo/demo.git",
        "rev": "develop",
    }


def test_add_directory_constraint_old_installer(
    app, repo, installer, mocker, old_tester
):
    p = mocker.patch("pathlib.Path.cwd")
    p.return_value = Path(__file__) / ".."

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))

    path = "../git/github.com/demo/demo"
    old_tester.execute("{}".format(path))

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.2 {})
""".format(
        app.poetry.file.parent.joinpath(path).resolve().as_posix()
    )

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {"path": "../git/github.com/demo/demo"}


def test_add_directory_with_poetry_old_installer(
    app, repo, installer, mocker, old_tester
):
    p = mocker.patch("pathlib.Path.cwd")
    p.return_value = Path(__file__) / ".."

    repo.add_package(get_package("pendulum", "1.4.4"))

    path = "../git/github.com/demo/pyproject-demo"
    old_tester.execute("{}".format(path))

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.2 {})
""".format(
        app.poetry.file.parent.joinpath(path).resolve().as_posix()
    )

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 2


def test_add_file_constraint_wheel_old_installer(
    app, repo, installer, mocker, old_tester
):
    p = mocker.patch("pathlib.Path.cwd")
    p.return_value = Path(__file__) / ".."

    repo.add_package(get_package("pendulum", "1.4.4"))

    path = "../distributions/demo-0.1.0-py2.py3-none-any.whl"
    old_tester.execute("{}".format(path))

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.0 {})
""".format(
        app.poetry.file.parent.joinpath(path).resolve().as_posix()
    )

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "path": "../distributions/demo-0.1.0-py2.py3-none-any.whl"
    }


def test_add_file_constraint_sdist_old_installer(
    app, repo, installer, mocker, old_tester
):
    p = mocker.patch("pathlib.Path.cwd")
    p.return_value = Path(__file__) / ".."

    repo.add_package(get_package("pendulum", "1.4.4"))

    path = "../distributions/demo-0.1.0.tar.gz"
    old_tester.execute("{}".format(path))

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.0 {})
""".format(
        app.poetry.file.parent.joinpath(path).resolve().as_posix()
    )

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "path": "../distributions/demo-0.1.0.tar.gz"
    }


def test_add_constraint_with_extras_option_old_installer(
    app, repo, installer, old_tester
):
    cachy2 = get_package("cachy", "0.2.0")
    cachy2.extras = {"msgpack": [get_dependency("msgpack-python")]}
    msgpack_dep = get_dependency("msgpack-python", ">=0.5 <0.6", optional=True)
    cachy2.add_dependency(msgpack_dep)

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    old_tester.execute("cachy=0.2.0 --extras msgpack")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing msgpack-python (0.5.3)
  - Installing cachy (0.2.0)
"""

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {
        "version": "0.2.0",
        "extras": ["msgpack"],
    }


def test_add_url_constraint_wheel_old_installer(
    app, repo, installer, mocker, old_tester
):
    p = mocker.patch("pathlib.Path.cwd")
    p.return_value = Path(__file__) / ".."

    repo.add_package(get_package("pendulum", "1.4.4"))

    old_tester.execute(
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

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "url": "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
    }


def test_add_url_constraint_wheel_with_extras_old_installer(
    app, repo, installer, old_tester
):
    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))
    repo.add_package(get_package("tomlkit", "0.5.5"))

    old_tester.execute(
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

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 4

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "url": "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl",
        "extras": ["foo", "bar"],
    }


def test_add_constraint_with_python_old_installer(app, repo, installer, old_tester):
    cachy2 = get_package("cachy", "0.2.0")

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)

    old_tester.execute("cachy=0.2.0 --python >=2.7")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)
"""

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {"version": "0.2.0", "python": ">=2.7"}


def test_add_constraint_with_platform_old_installer(
    app, repo, installer, env, old_tester
):
    platform = sys.platform
    env._platform = platform

    cachy2 = get_package("cachy", "0.2.0")

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)

    old_tester.execute("cachy=0.2.0 --platform {} -vvv".format(platform))

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)
"""

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {
        "version": "0.2.0",
        "platform": platform,
    }


def test_add_constraint_with_source_old_installer(app, poetry, installer, old_tester):
    repo = LegacyRepository(name="my-index", url="https://my-index.fake")
    repo.add_package(get_package("cachy", "0.2.0"))
    repo._cache.store("matches").put("cachy:0.2.0", [Version.parse("0.2.0")], 5)

    poetry.pool.add_repository(repo)

    old_tester.execute("cachy=0.2.0 --source my-index")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)
"""

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {
        "version": "0.2.0",
        "source": "my-index",
    }


def test_add_constraint_with_source_that_does_not_exist_old_installer(app, old_tester):
    with pytest.raises(ValueError) as e:
        old_tester.execute("foo --source i-dont-exist")

    assert 'Repository "i-dont-exist" does not exist.' == str(e.value)


def test_add_constraint_not_found_with_source_old_installer(
    app, poetry, mocker, old_tester
):
    repo = LegacyRepository(name="my-index", url="https://my-index.fake")
    mocker.patch.object(repo, "find_packages", return_value=[])

    poetry.pool.add_repository(repo)

    pypi = poetry.pool.repositories[0]
    pypi.add_package(get_package("cachy", "0.2.0"))

    with pytest.raises(ValueError) as e:
        old_tester.execute("cachy --source my-index")

    assert "Could not find a matching version of package cachy" == str(e.value)


def test_add_to_section_that_does_no_exist_yet_old_installer(
    app, repo, installer, old_tester
):
    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    old_tester.execute("cachy --group dev")

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)
"""

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["group"]["dev"]["dependencies"]
    assert content["group"]["dev"]["dependencies"]["cachy"] == "^0.2.0"


def test_add_should_not_select_prereleases_old_installer(
    app, repo, installer, old_tester
):
    repo.add_package(get_package("pyyaml", "3.13"))
    repo.add_package(get_package("pyyaml", "4.2b2"))

    old_tester.execute("pyyaml")

    expected = """\
Using version ^3.13 for pyyaml

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing pyyaml (3.13)
"""

    assert expected == old_tester.io.fetch_output()

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "pyyaml" in content["dependencies"]
    assert content["dependencies"]["pyyaml"] == "^3.13"


def test_add_should_skip_when_adding_existing_package_with_no_constraint_old_installer(
    app, repo, installer, old_tester
):
    content = app.poetry.file.read()
    content["tool"]["poetry"]["dependencies"]["foo"] = "^1.0"
    app.poetry.file.write(content)

    repo.add_package(get_package("foo", "1.1.2"))

    old_tester.execute("foo")

    expected = """\
The following packages are already present in the pyproject.toml and will be skipped:

  • foo

If you want to update it to the latest compatible version, you can use `poetry update package`.
If you prefer to upgrade it to the latest available version, you can use `poetry add package@latest`.
"""

    assert expected in old_tester.io.fetch_output()


def test_add_should_work_when_adding_existing_package_with_latest_constraint_old_installer(
    app, repo, installer, old_tester
):
    content = app.poetry.file.read()
    content["tool"]["poetry"]["dependencies"]["foo"] = "^1.0"
    app.poetry.file.write(content)

    repo.add_package(get_package("foo", "1.1.2"))

    old_tester.execute("foo@latest")

    expected = """\
Using version ^1.1.2 for foo

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing foo (1.1.2)
"""

    assert expected in old_tester.io.fetch_output()

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "foo" in content["dependencies"]
    assert content["dependencies"]["foo"] == "^1.1.2"


def test_add_chooses_prerelease_if_only_prereleases_are_available_old_installer(
    app, repo, installer, old_tester
):
    repo.add_package(get_package("foo", "1.2.3b0"))
    repo.add_package(get_package("foo", "1.2.3b1"))

    old_tester.execute("foo")

    expected = """\
Using version ^1.2.3-beta.1 for foo

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing foo (1.2.3b1)
"""

    assert expected in old_tester.io.fetch_output()


def test_add_preferes_stable_releases_old_installer(app, repo, installer, old_tester):
    repo.add_package(get_package("foo", "1.2.3"))
    repo.add_package(get_package("foo", "1.2.4b1"))

    old_tester.execute("foo")

    expected = """\
Using version ^1.2.3 for foo

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing foo (1.2.3)
"""

    assert expected in old_tester.io.fetch_output()


def test_add_with_lock_old_installer(app, repo, installer, old_tester):
    repo.add_package(get_package("cachy", "0.2.0"))

    old_tester.execute("cachy --lock")

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...

Writing lock file
"""

    assert expected == old_tester.io.fetch_output()


def test_add_keyboard_interrupt_restore_content(app, repo, installer, tester, mocker):
    mocker.patch(
        "poetry.installation.installer.Installer.run", side_effect=KeyboardInterrupt()
    )
    original_content = app.poetry.file.read()

    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy --dry-run")

    assert original_content == app.poetry.file.read()


def test_dry_run_restore_original_content(app, repo, installer, tester):
    original_content = app.poetry.file.read()

    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy --dry-run")

    assert original_content == app.poetry.file.read()
