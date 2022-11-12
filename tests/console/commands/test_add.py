from __future__ import annotations

import sys

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.core.constraints.version import Version
from poetry.core.packages.package import Package

from poetry.repositories.legacy_repository import LegacyRepository
from tests.helpers import get_dependency
from tests.helpers import get_package


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.installation.noop_installer import NoopInstaller
    from poetry.poetry import Poetry
    from poetry.utils.env import MockEnv
    from poetry.utils.env import VirtualEnv
    from tests.helpers import PoetryTestApplication
    from tests.helpers import TestRepository
    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter
    from tests.types import ProjectFactory


@pytest.fixture
def poetry_with_up_to_date_lockfile(
    project_factory: ProjectFactory, fixture_dir: FixtureDirGetter
) -> Poetry:
    source = fixture_dir("up_to_date_lock")

    return project_factory(
        name="foobar",
        pyproject_content=(source / "pyproject.toml").read_text(encoding="utf-8"),
        poetry_lock_content=(source / "poetry.lock").read_text(encoding="utf-8"),
    )


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("add")


@pytest.fixture()
def old_tester(tester: CommandTester) -> CommandTester:
    tester.command.installer.use_executor(False)

    return tester


def test_add_no_constraint(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
):
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

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == "^0.2.0"


def test_add_replace_by_constraint(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
):
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
    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == "^0.2.0"

    tester.execute("cachy@0.1.0")
    expected = """
Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing cachy (0.1.0)
"""
    assert tester.io.fetch_output() == expected

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == "0.1.0"


def test_add_no_constraint_editable_error(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
):
    content = app.poetry.file.read()["tool"]["poetry"]

    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("-e cachy")

    expected = """
Failed to add packages. Only vcs/path dependencies support editable installs.\
 cachy is neither.

No changes were applied.
"""
    assert tester.status_code == 1
    assert tester.io.fetch_error() == expected
    assert tester.command.installer.executor.installations_count == 0
    assert content == app.poetry.file.read()["tool"]["poetry"]


def test_add_equal_constraint(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
):
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

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 1


def test_add_greater_constraint(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
):
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

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 1


@pytest.mark.parametrize("extra_name", ["msgpack", "MsgPack"])
def test_add_constraint_with_extras(
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
    extra_name: str,
):
    cachy1 = get_package("cachy", "0.1.0")
    cachy1.extras = {"msgpack": [get_dependency("msgpack-python")]}
    msgpack_dep = get_dependency("msgpack-python", ">=0.5 <0.6", optional=True)
    cachy1.add_dependency(msgpack_dep)

    repo.add_package(get_package("cachy", "0.2.0"))
    repo.add_package(cachy1)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    tester.execute(f"cachy[{extra_name}]>=0.1.0,<0.2.0")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  • Installing msgpack-python (0.5.3)
  • Installing cachy (0.1.0)
"""

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 2


def test_add_constraint_dependencies(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
):
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

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 2


def test_add_git_constraint(
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
    tmp_venv: VirtualEnv,
):
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

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "git": "https://github.com/demo/demo.git"
    }


def test_add_git_constraint_with_poetry(
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
    tmp_venv: VirtualEnv,
):
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

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 2


@pytest.mark.parametrize("extra_name", ["foo", "FOO"])
def test_add_git_constraint_with_extras(
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
    tmp_venv: VirtualEnv,
    extra_name: str,
):
    tester.command.set_env(tmp_venv)

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))
    repo.add_package(get_package("tomlkit", "0.5.5"))

    tester.execute(f"git+https://github.com/demo/demo.git[{extra_name},bar]")

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

    assert tester.io.fetch_output().strip() == expected.strip()
    assert tester.command.installer.executor.installations_count == 4

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "git": "https://github.com/demo/demo.git",
        "extras": [extra_name, "bar"],
    }


@pytest.mark.parametrize(
    "url, rev",
    [
        ("git+https://github.com/demo/subdirectories.git#subdirectory=two", None),
        (
            "git+https://github.com/demo/subdirectories.git@master#subdirectory=two",
            "master",
        ),
    ],
)
def test_add_git_constraint_with_subdirectory(
    url: str,
    rev: str | None,
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
    env: MockEnv,
):
    tester.execute(url)

    expected = """\
Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing two (2.0.0 9cf87a2)
"""
    assert tester.io.fetch_output().strip() == expected.strip()
    assert tester.command.installer.executor.installations_count == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    constraint = {
        "git": "https://github.com/demo/subdirectories.git",
        "subdirectory": "two",
    }

    if rev:
        constraint["rev"] = rev

    assert "two" in content["dependencies"]
    assert content["dependencies"]["two"] == constraint


@pytest.mark.parametrize("editable", [False, True])
def test_add_git_ssh_constraint(
    editable: bool,
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
    tmp_venv: VirtualEnv,
):
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

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]

    expected = {
        "git": "ssh://git@github.com/demo/demo.git",
        "rev": "develop",
    }
    if editable:
        expected["develop"] = True

    assert content["dependencies"]["demo"] == expected


@pytest.mark.parametrize(
    "required_fixtures",
    [["git/github.com/demo/demo"]],
)
@pytest.mark.parametrize("editable", [False, True])
def test_add_directory_constraint(
    editable: bool,
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
):
    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))

    path = "../git/github.com/demo/demo"
    tester.execute(f"{path}" if not editable else f"-e {path}")

    expected = f"""\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  • Installing pendulum (1.4.4)
  • Installing demo (0.1.2 {app.poetry.file.parent.joinpath(path).resolve().as_posix()})
"""

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]

    expected = {"path": path}
    if editable:
        expected["develop"] = True

    assert content["dependencies"]["demo"] == expected


@pytest.mark.parametrize(
    "required_fixtures",
    [["git/github.com/demo/pyproject-demo"]],
)
def test_add_directory_with_poetry(
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
):
    repo.add_package(get_package("pendulum", "1.4.4"))

    path = "../git/github.com/demo/pyproject-demo"
    tester.execute(f"{path}")

    expected = f"""\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  • Installing pendulum (1.4.4)
  • Installing demo (0.1.2 {app.poetry.file.parent.joinpath(path).resolve().as_posix()})
"""

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 2


@pytest.mark.parametrize(
    "required_fixtures",
    [["distributions/demo-0.1.0-py2.py3-none-any.whl"]],
)
def test_add_file_constraint_wheel(
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
    poetry: Poetry,
):
    repo.add_package(get_package("pendulum", "1.4.4"))

    path = "../distributions/demo-0.1.0-py2.py3-none-any.whl"
    tester.execute(f"{path}")

    expected = f"""\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  • Installing pendulum (1.4.4)
  • Installing demo (0.1.0 {app.poetry.file.parent.joinpath(path).resolve().as_posix()})
"""

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {"path": path}


@pytest.mark.parametrize(
    "required_fixtures",
    [["distributions/demo-0.1.0.tar.gz"]],
)
def test_add_file_constraint_sdist(
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
):
    repo.add_package(get_package("pendulum", "1.4.4"))

    path = "../distributions/demo-0.1.0.tar.gz"
    tester.execute(f"{path}")

    expected = f"""\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  • Installing pendulum (1.4.4)
  • Installing demo (0.1.0 {app.poetry.file.parent.joinpath(path).resolve().as_posix()})
"""

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {"path": path}


@pytest.mark.parametrize("extra_name", ["msgpack", "MsgPack"])
def test_add_constraint_with_extras_option(
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
    extra_name: str,
):
    cachy2 = get_package("cachy", "0.2.0")
    cachy2.extras = {"msgpack": [get_dependency("msgpack-python")]}
    msgpack_dep = get_dependency("msgpack-python", ">=0.5 <0.6", optional=True)
    cachy2.add_dependency(msgpack_dep)

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    tester.execute(f"cachy=0.2.0 --extras {extra_name}")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  • Installing msgpack-python (0.5.3)
  • Installing cachy (0.2.0)
"""

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {
        "version": "0.2.0",
        "extras": [extra_name],
    }


def test_add_url_constraint_wheel(
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
    mocker: MockerFixture,
):
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
  • Installing demo\
 (0.1.0 https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl)
"""

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "url": "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
    }


@pytest.mark.parametrize("extra_name", ["foo", "FOO"])
def test_add_url_constraint_wheel_with_extras(
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
    extra_name: str,
    mocker: MockerFixture,
):
    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))
    repo.add_package(get_package("tomlkit", "0.5.5"))

    tester.execute(
        "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
        f"[{extra_name},bar]"
    )

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 4 installs, 0 updates, 0 removals

  • Installing cleo (0.6.5)
  • Installing pendulum (1.4.4)
  • Installing tomlkit (0.5.5)
  • Installing demo\
 (0.1.0 https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl)
"""
    # Order might be different, split into lines and compare the overall output.
    expected = set(expected.splitlines())
    output = set(tester.io.fetch_output().splitlines())
    assert output == expected
    assert tester.command.installer.executor.installations_count == 4

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "url": (
            "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
        ),
        "extras": [extra_name, "bar"],
    }


def test_add_constraint_with_python(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
):
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

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {"version": "0.2.0", "python": ">=2.7"}


def test_add_constraint_with_platform(
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
    env: MockEnv,
):
    platform = sys.platform
    env._platform = platform

    cachy2 = get_package("cachy", "0.2.0")

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)

    tester.execute(f"cachy=0.2.0 --platform {platform} -vvv")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing cachy (0.2.0)
"""

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {
        "version": "0.2.0",
        "platform": platform,
    }


def test_add_constraint_with_source(
    app: PoetryTestApplication,
    poetry: Poetry,
    tester: CommandTester,
    mocker: MockerFixture,
):
    repo = LegacyRepository(name="my-index", url="https://my-index.fake")
    repo.add_package(get_package("cachy", "0.2.0"))
    mocker.patch.object(
        repo,
        "_find_packages",
        wraps=lambda _, name: [
            Package(
                "cachy",
                Version.parse("0.2.0"),
                source_type="legacy",
                source_reference=repo.name,
                source_url=repo._url,
                yanked=False,
            )
        ],
    )

    poetry.pool.add_repository(repo)

    tester.execute("cachy=0.2.0 --source my-index")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing cachy (0.2.0)
"""

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {
        "version": "0.2.0",
        "source": "my-index",
    }


def test_add_constraint_with_source_that_does_not_exist(
    app: PoetryTestApplication, tester: CommandTester
):
    with pytest.raises(IndexError) as e:
        tester.execute("foo --source i-dont-exist")

    assert str(e.value) == 'Repository "i-dont-exist" does not exist.'


def test_add_constraint_not_found_with_source(
    app: PoetryTestApplication,
    poetry: Poetry,
    mocker: MockerFixture,
    tester: CommandTester,
):
    repo = LegacyRepository(name="my-index", url="https://my-index.fake")
    mocker.patch.object(repo, "find_packages", return_value=[])

    poetry.pool.add_repository(repo)

    pypi = poetry.pool.repositories[0]
    pypi.add_package(get_package("cachy", "0.2.0"))

    with pytest.raises(ValueError) as e:
        tester.execute("cachy --source my-index")

    assert str(e.value) == "Could not find a matching version of package cachy"


def test_add_to_section_that_does_not_exist_yet(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
):
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

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["group"]["dev"]["dependencies"]
    assert content["group"]["dev"]["dependencies"]["cachy"] == "^0.2.0"

    expected = """\

[tool.poetry.group.dev.dependencies]
cachy = "^0.2.0"

"""
    string_content = content.as_string()
    if "\r\n" in string_content:
        # consistent line endings
        expected = expected.replace("\n", "\r\n")

    assert expected in string_content


def test_add_to_dev_section_deprecated(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
):
    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy --dev")

    warning = """\
The --dev option is deprecated, use the `--group dev` notation instead.
"""

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing cachy (0.2.0)
"""

    assert tester.io.fetch_error() == warning
    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["group"]["dev"]["dependencies"]
    assert content["group"]["dev"]["dependencies"]["cachy"] == "^0.2.0"


def test_add_should_not_select_prereleases(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
):
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

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "pyyaml" in content["dependencies"]
    assert content["dependencies"]["pyyaml"] == "^3.13"


def test_add_should_skip_when_adding_existing_package_with_no_constraint(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
):
    content = app.poetry.file.read()
    content["tool"]["poetry"]["dependencies"]["foo"] = "^1.0"
    app.poetry.file.write(content)

    repo.add_package(get_package("foo", "1.1.2"))
    tester.execute("foo")

    expected = """\
The following packages are already present in the pyproject.toml and will be skipped:

  • foo

If you want to update it to the latest compatible version,\
 you can use `poetry update package`.
If you prefer to upgrade it to the latest available version,\
 you can use `poetry add package@latest`.
"""

    assert expected in tester.io.fetch_output()


def test_add_should_skip_when_adding_canonicalized_existing_package_with_no_constraint(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
):
    content = app.poetry.file.read()
    content["tool"]["poetry"]["dependencies"]["foo-bar"] = "^1.0"
    app.poetry.file.write(content)

    repo.add_package(get_package("foo-bar", "1.1.2"))
    tester.execute("Foo_Bar")

    expected = """\
The following packages are already present in the pyproject.toml and will be skipped:

  • Foo_Bar

If you want to update it to the latest compatible version,\
 you can use `poetry update package`.
If you prefer to upgrade it to the latest available version,\
 you can use `poetry add package@latest`.
"""

    assert expected in tester.io.fetch_output()


def test_add_latest_should_not_create_duplicate_keys(
    project_factory: ProjectFactory,
    repo: TestRepository,
    command_tester_factory: CommandTesterFactory,
):
    pyproject_content = """\
    [tool.poetry]
    name = "simple-project"
    version = "1.2.3"
    description = "Some description."
    authors = [
        "Python Poetry <tests@python-poetry.org>"
    ]
    license = "MIT"
    readme = "README.md"

    [tool.poetry.dependencies]
    python = "^3.6"
    Foo = "^0.6"
    """

    poetry = project_factory(name="simple-project", pyproject_content=pyproject_content)
    content = poetry.file.read()

    assert "Foo" in content["tool"]["poetry"]["dependencies"]
    assert content["tool"]["poetry"]["dependencies"]["Foo"] == "^0.6"
    assert "foo" not in content["tool"]["poetry"]["dependencies"]

    tester = command_tester_factory("add", poetry=poetry)
    repo.add_package(get_package("foo", "1.1.2"))
    tester.execute("foo@latest")

    updated_content = poetry.file.read()
    assert "Foo" in updated_content["tool"]["poetry"]["dependencies"]
    assert updated_content["tool"]["poetry"]["dependencies"]["Foo"] == "^1.1.2"
    assert "foo" not in updated_content["tool"]["poetry"]["dependencies"]


def test_add_should_work_when_adding_existing_package_with_latest_constraint(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
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


def test_add_chooses_prerelease_if_only_prereleases_are_available(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
):
    repo.add_package(get_package("foo", "1.2.3b0"))
    repo.add_package(get_package("foo", "1.2.3b1"))

    tester.execute("foo")

    expected = """\
Using version ^1.2.3b1 for foo

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing foo (1.2.3b1)
"""
    assert expected in tester.io.fetch_output()


def test_add_prefers_stable_releases(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
):
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


def test_add_with_lock(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
):
    content_hash = app.poetry.locker._get_content_hash()
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy --lock")

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...

Writing lock file
"""

    assert tester.io.fetch_output() == expected
    assert content_hash != app.poetry.locker.lock_data["metadata"]["content-hash"]


def test_add_no_constraint_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
):
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

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == "^0.2.0"


def test_add_equal_constraint_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
):
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

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 1


def test_add_greater_constraint_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
):
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

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 1


@pytest.mark.parametrize("extra_name", ["msgpack", "MsgPack"])
def test_add_constraint_with_extras_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
    extra_name: str,
):
    cachy1 = get_package("cachy", "0.1.0")
    cachy1.extras = {"msgpack": [get_dependency("msgpack-python")]}
    msgpack_dep = get_dependency("msgpack-python", ">=0.5 <0.6", optional=True)
    cachy1.add_dependency(msgpack_dep)

    repo.add_package(get_package("cachy", "0.2.0"))
    repo.add_package(cachy1)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    old_tester.execute(f"cachy[{extra_name}]>=0.1.0,<0.2.0")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing msgpack-python (0.5.3)
  - Installing cachy (0.1.0)
"""

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 2


def test_add_constraint_dependencies_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
):
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

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 2


def test_add_git_constraint_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
):
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

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "git": "https://github.com/demo/demo.git"
    }


def test_add_git_constraint_with_poetry_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
):
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

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 2


@pytest.mark.parametrize("extra_name", ["foo", "FOO"])
def test_add_git_constraint_with_extras_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
    extra_name: str,
):
    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))
    repo.add_package(get_package("tomlkit", "0.5.5"))

    old_tester.execute(f"git+https://github.com/demo/demo.git[{extra_name},bar]")

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

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 4

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "git": "https://github.com/demo/demo.git",
        "extras": [extra_name, "bar"],
    }


def test_add_git_ssh_constraint_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
):
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

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "git": "ssh://git@github.com/demo/demo.git",
        "rev": "develop",
    }


@pytest.mark.parametrize(
    "required_fixtures",
    [["git/github.com/demo/demo"]],
)
def test_add_directory_constraint_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
):
    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))

    path = "../git/github.com/demo/demo"
    old_tester.execute(f"{path}")

    expected = f"""\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.2 {app.poetry.file.parent.joinpath(path).resolve().as_posix()})
"""

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {"path": path}


@pytest.mark.parametrize(
    "required_fixtures",
    [["git/github.com/demo/pyproject-demo"]],
)
def test_add_directory_with_poetry_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
):
    repo.add_package(get_package("pendulum", "1.4.4"))

    path = "../git/github.com/demo/pyproject-demo"
    old_tester.execute(f"{path}")

    expected = f"""\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.2 {app.poetry.file.parent.joinpath(path).resolve().as_posix()})
"""

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 2


@pytest.mark.parametrize(
    "required_fixtures",
    [["distributions/demo-0.1.0-py2.py3-none-any.whl"]],
)
def test_add_file_constraint_wheel_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
):
    repo.add_package(get_package("pendulum", "1.4.4"))

    path = "../distributions/demo-0.1.0-py2.py3-none-any.whl"
    old_tester.execute(f"{path}")

    expected = f"""\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.0 {app.poetry.file.parent.joinpath(path).resolve().as_posix()})
"""

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {"path": path}


@pytest.mark.parametrize(
    "required_fixtures",
    [["distributions/demo-0.1.0.tar.gz"]],
)
def test_add_file_constraint_sdist_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
):
    repo.add_package(get_package("pendulum", "1.4.4"))

    path = "../distributions/demo-0.1.0.tar.gz"
    old_tester.execute(f"{path}")

    expected = f"""\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.0 {app.poetry.file.parent.joinpath(path).resolve().as_posix()})
"""

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {"path": path}


@pytest.mark.parametrize("extra_name", ["msgpack", "MsgPack"])
def test_add_constraint_with_extras_option_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
    extra_name: str,
):
    cachy2 = get_package("cachy", "0.2.0")
    cachy2.extras = {"msgpack": [get_dependency("msgpack-python")]}
    msgpack_dep = get_dependency("msgpack-python", ">=0.5 <0.6", optional=True)
    cachy2.add_dependency(msgpack_dep)

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    old_tester.execute(f"cachy=0.2.0 --extras {extra_name}")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  - Installing msgpack-python (0.5.3)
  - Installing cachy (0.2.0)
"""

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {
        "version": "0.2.0",
        "extras": [extra_name],
    }


def test_add_url_constraint_wheel_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    mocker: MockerFixture,
    old_tester: CommandTester,
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
  - Installing demo\
 (0.1.0 https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl)
"""

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 2

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "url": "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
    }


@pytest.mark.parametrize("extra_name", ["foo", "FOO"])
def test_add_url_constraint_wheel_with_extras_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
    extra_name: str,
):
    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))
    repo.add_package(get_package("tomlkit", "0.5.5"))

    old_tester.execute(
        "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
        f"[{extra_name},bar]"
    )

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 4 installs, 0 updates, 0 removals

  - Installing cleo (0.6.5)
  - Installing pendulum (1.4.4)
  - Installing tomlkit (0.5.5)
  - Installing demo\
 (0.1.0 https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl)
"""

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 4

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "url": (
            "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
        ),
        "extras": [extra_name, "bar"],
    }


def test_add_constraint_with_python_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
):
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

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {"version": "0.2.0", "python": ">=2.7"}


def test_add_constraint_with_platform_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    env: MockEnv,
    old_tester: CommandTester,
):
    platform = sys.platform
    env._platform = platform

    cachy2 = get_package("cachy", "0.2.0")

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)

    old_tester.execute(f"cachy=0.2.0 --platform {platform} -vvv")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)
"""

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {
        "version": "0.2.0",
        "platform": platform,
    }


def test_add_constraint_with_source_old_installer(
    app: PoetryTestApplication,
    poetry: Poetry,
    installer: NoopInstaller,
    old_tester: CommandTester,
    mocker: MockerFixture,
):
    repo = LegacyRepository(name="my-index", url="https://my-index.fake")
    repo.add_package(get_package("cachy", "0.2.0"))
    mocker.patch.object(
        repo,
        "_find_packages",
        wraps=lambda _, name: [
            Package(
                "cachy",
                Version.parse("0.2.0"),
                source_type="legacy",
                source_reference=repo.name,
                source_url=repo._url,
                yanked=False,
            )
        ],
    )

    poetry.pool.add_repository(repo)

    old_tester.execute("cachy=0.2.0 --source my-index")

    expected = """\

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)
"""

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {
        "version": "0.2.0",
        "source": "my-index",
    }


def test_add_constraint_with_source_that_does_not_exist_old_installer(
    app: PoetryTestApplication, old_tester: CommandTester
):
    with pytest.raises(IndexError) as e:
        old_tester.execute("foo --source i-dont-exist")

    assert str(e.value) == 'Repository "i-dont-exist" does not exist.'


def test_add_constraint_not_found_with_source_old_installer(
    app: PoetryTestApplication,
    poetry: Poetry,
    mocker: MockerFixture,
    old_tester: CommandTester,
):
    repo = LegacyRepository(name="my-index", url="https://my-index.fake")
    mocker.patch.object(repo, "find_packages", return_value=[])

    poetry.pool.add_repository(repo)

    pypi = poetry.pool.repositories[0]
    pypi.add_package(get_package("cachy", "0.2.0"))

    with pytest.raises(ValueError) as e:
        old_tester.execute("cachy --source my-index")

    assert str(e.value) == "Could not find a matching version of package cachy"


def test_add_to_section_that_does_no_exist_yet_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
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

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["group"]["dev"]["dependencies"]
    assert content["group"]["dev"]["dependencies"]["cachy"] == "^0.2.0"


def test_add_should_not_select_prereleases_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
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

    assert old_tester.io.fetch_output() == expected

    assert len(installer.installs) == 1

    content = app.poetry.file.read()["tool"]["poetry"]

    assert "pyyaml" in content["dependencies"]
    assert content["dependencies"]["pyyaml"] == "^3.13"


def test_add_should_skip_when_adding_existing_package_with_no_constraint_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
):
    content = app.poetry.file.read()
    content["tool"]["poetry"]["dependencies"]["foo"] = "^1.0"
    app.poetry.file.write(content)

    repo.add_package(get_package("foo", "1.1.2"))

    old_tester.execute("foo")

    expected = """\
The following packages are already present in the pyproject.toml and will be skipped:

  • foo

If you want to update it to the latest compatible version,\
 you can use `poetry update package`.
If you prefer to upgrade it to the latest available version,\
 you can use `poetry add package@latest`.
"""

    assert expected in old_tester.io.fetch_output()


def test_add_should_work_when_adding_existing_package_with_latest_constraint_old_installer(  # noqa: E501
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
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
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
):
    repo.add_package(get_package("foo", "1.2.3b0"))
    repo.add_package(get_package("foo", "1.2.3b1"))

    old_tester.execute("foo")

    expected = """\
Using version ^1.2.3b1 for foo

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  - Installing foo (1.2.3b1)
"""
    assert expected in old_tester.io.fetch_output()


def test_add_preferes_stable_releases_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
):
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


def test_add_with_lock_old_installer(
    app: PoetryTestApplication,
    repo: TestRepository,
    installer: NoopInstaller,
    old_tester: CommandTester,
):
    repo.add_package(get_package("cachy", "0.2.0"))

    old_tester.execute("cachy --lock")

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...

Writing lock file
"""

    assert old_tester.io.fetch_output() == expected


def test_add_keyboard_interrupt_restore_content(
    poetry_with_up_to_date_lockfile: Poetry,
    repo: TestRepository,
    command_tester_factory: CommandTesterFactory,
    mocker: MockerFixture,
):
    tester = command_tester_factory("add", poetry=poetry_with_up_to_date_lockfile)

    mocker.patch(
        "poetry.installation.installer.Installer.run", side_effect=KeyboardInterrupt()
    )
    original_pyproject_content = poetry_with_up_to_date_lockfile.file.read()
    original_lockfile_content = poetry_with_up_to_date_lockfile._locker.lock_data

    repo.add_package(get_package("cachy", "0.2.0"))
    repo.add_package(get_package("docker", "4.3.1"))

    tester.execute("cachy")

    assert poetry_with_up_to_date_lockfile.file.read() == original_pyproject_content
    assert (
        poetry_with_up_to_date_lockfile._locker.lock_data == original_lockfile_content
    )


@pytest.mark.parametrize(
    "command",
    [
        "cachy --dry-run",
        "cachy --lock --dry-run",
    ],
)
def test_add_with_dry_run_keep_files_intact(
    command: str,
    poetry_with_up_to_date_lockfile: Poetry,
    repo: TestRepository,
    command_tester_factory: CommandTesterFactory,
):
    tester = command_tester_factory("add", poetry=poetry_with_up_to_date_lockfile)

    original_pyproject_content = poetry_with_up_to_date_lockfile.file.read()
    original_lockfile_content = poetry_with_up_to_date_lockfile._locker.lock_data

    repo.add_package(get_package("cachy", "0.2.0"))
    repo.add_package(get_package("docker", "4.3.1"))

    tester.execute(command)

    assert poetry_with_up_to_date_lockfile.file.read() == original_pyproject_content
    assert (
        poetry_with_up_to_date_lockfile._locker.lock_data == original_lockfile_content
    )
