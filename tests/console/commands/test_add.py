from __future__ import annotations

import sys

from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import pytest

from packaging.utils import canonicalize_name
from poetry.core.constraints.version import Version
from poetry.core.packages.package import Package

from poetry.console.commands.installer_command import InstallerCommand
from poetry.puzzle.exceptions import SolverProblemError
from poetry.repositories.legacy_repository import LegacyRepository
from tests.helpers import TestLocker
from tests.helpers import get_dependency
from tests.helpers import get_package


if TYPE_CHECKING:
    from typing import Any

    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture
    from tomlkit import TOMLDocument

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


@pytest.fixture
def poetry_with_path_dependency(
    project_factory: ProjectFactory, fixture_dir: FixtureDirGetter
) -> Poetry:
    source = fixture_dir("with_path_dependency")

    poetry = project_factory(
        name="foobar",
        source=source,
        use_test_locker=False,
    )
    return poetry


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("add")


def test_add_no_constraint(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
) -> None:
    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy")

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)

Writing lock file
"""

    assert tester.io.fetch_output() == expected
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 1

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == "^0.2.0"


def test_add_replace_by_constraint(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
) -> None:
    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy")

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)

Writing lock file
"""
    assert tester.io.fetch_output() == expected
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 1

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == "^0.2.0"

    tester.execute("cachy@0.1.0")
    expected = """
Updating dependencies
Resolving dependencies...

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.1.0)

Writing lock file
"""
    assert tester.io.fetch_output() == expected

    pyproject2: dict[str, Any] = app.poetry.file.read()
    content = pyproject2["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == "0.1.0"


def test_add_no_constraint_editable_error(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
) -> None:
    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("-e cachy")

    expected = """
Failed to add packages. Only vcs/path dependencies support editable installs.\
 cachy is neither.

No changes were applied.
"""
    assert tester.status_code == 1
    assert tester.io.fetch_error() == expected
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 0

    pyproject2: dict[str, Any] = app.poetry.file.read()
    assert content == pyproject2["tool"]["poetry"]


def test_add_equal_constraint(repo: TestRepository, tester: CommandTester) -> None:
    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy==0.1.0")

    expected = """\

Updating dependencies
Resolving dependencies...

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.1.0)

Writing lock file
"""

    assert tester.io.fetch_output() == expected
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 1


def test_add_greater_constraint(repo: TestRepository, tester: CommandTester) -> None:
    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy>=0.1.0")

    expected = """\

Updating dependencies
Resolving dependencies...

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)

Writing lock file
"""

    assert tester.io.fetch_output() == expected
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 1


@pytest.mark.parametrize("extra_name", ["msgpack", "MsgPack"])
def test_add_constraint_with_extras(
    repo: TestRepository,
    tester: CommandTester,
    extra_name: str,
) -> None:
    cachy1 = get_package("cachy", "0.1.0")
    cachy1.extras = {canonicalize_name("msgpack"): [get_dependency("msgpack-python")]}
    msgpack_dep = get_dependency("msgpack-python", ">=0.5 <0.6", optional=True)
    cachy1.add_dependency(msgpack_dep)

    repo.add_package(get_package("cachy", "0.2.0"))
    repo.add_package(cachy1)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    tester.execute(f"cachy[{extra_name}]>=0.1.0,<0.2.0")

    expected = """\

Updating dependencies
Resolving dependencies...

Package operations: 2 installs, 0 updates, 0 removals

  - Installing msgpack-python (0.5.3)
  - Installing cachy (0.1.0)

Writing lock file
"""

    assert tester.io.fetch_output() == expected
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 2


def test_add_constraint_dependencies(
    repo: TestRepository, tester: CommandTester
) -> None:
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

Package operations: 2 installs, 0 updates, 0 removals

  - Installing msgpack-python (0.5.3)
  - Installing cachy (0.2.0)

Writing lock file
"""

    assert tester.io.fetch_output() == expected
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 2


def test_add_git_constraint(
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
    tmp_venv: VirtualEnv,
) -> None:
    assert isinstance(tester.command, InstallerCommand)
    tester.command.set_env(tmp_venv)

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))

    tester.execute("git+https://github.com/demo/demo.git")

    expected = """\

Updating dependencies
Resolving dependencies...

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.2 9cf87a2)

Writing lock file
"""

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 2

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "git": "https://github.com/demo/demo.git"
    }


def test_add_git_constraint_with_poetry(
    repo: TestRepository,
    tester: CommandTester,
    tmp_venv: VirtualEnv,
) -> None:
    assert isinstance(tester.command, InstallerCommand)
    tester.command.set_env(tmp_venv)

    repo.add_package(get_package("pendulum", "1.4.4"))

    tester.execute("git+https://github.com/demo/pyproject-demo.git")

    expected = """\

Updating dependencies
Resolving dependencies...

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.2 9cf87a2)

Writing lock file
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
) -> None:
    assert isinstance(tester.command, InstallerCommand)
    tester.command.set_env(tmp_venv)

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))
    repo.add_package(get_package("tomlkit", "0.5.5"))

    tester.execute(f"git+https://github.com/demo/demo.git[{extra_name},bar]")

    expected = """\

Updating dependencies
Resolving dependencies...

Package operations: 4 installs, 0 updates, 0 removals

  - Installing cleo (0.6.5)
  - Installing pendulum (1.4.4)
  - Installing tomlkit (0.5.5)
  - Installing demo (0.1.2 9cf87a2)

Writing lock file
"""

    assert tester.io.fetch_output().strip() == expected.strip()
    assert tester.command.installer.executor.installations_count == 4

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

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
    tester: CommandTester,
) -> None:
    tester.execute(url)

    expected = """\
Updating dependencies
Resolving dependencies...

Package operations: 1 install, 0 updates, 0 removals

  - Installing two (2.0.0 9cf87a2)

Writing lock file
"""
    assert tester.io.fetch_output().strip() == expected.strip()
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 1

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

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
) -> None:
    assert isinstance(tester.command, InstallerCommand)
    tester.command.set_env(tmp_venv)

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))

    url = "git+ssh://git@github.com/demo/demo.git@develop"
    tester.execute(f"{url}" if not editable else f"-e {url}")

    expected = """\

Updating dependencies
Resolving dependencies...

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.2 9cf87a2)

Writing lock file
"""

    assert tester.io.fetch_output() == expected
    assert tester.command.installer.executor.installations_count == 2

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

    assert "demo" in content["dependencies"]

    expected_content: dict[str, Any] = {
        "git": "ssh://git@github.com/demo/demo.git",
        "rev": "develop",
    }
    if editable:
        expected_content["develop"] = True

    assert content["dependencies"]["demo"] == expected_content


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
) -> None:
    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "0.6.5"))

    path = "../git/github.com/demo/demo"
    tester.execute(f"{path}" if not editable else f"-e {path}")

    demo_path = app.poetry.file.path.parent.joinpath(path).resolve().as_posix()
    expected = f"""\

Updating dependencies
Resolving dependencies...

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.2 {demo_path})

Writing lock file
"""

    assert tester.io.fetch_output() == expected
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 2

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

    assert "demo" in content["dependencies"]

    expected_content: dict[str, Any] = {"path": path}
    if editable:
        expected_content["develop"] = True

    assert content["dependencies"]["demo"] == expected_content


@pytest.mark.parametrize(
    "required_fixtures",
    [["git/github.com/demo/pyproject-demo"]],
)
def test_add_directory_with_poetry(
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
) -> None:
    repo.add_package(get_package("pendulum", "1.4.4"))

    path = "../git/github.com/demo/pyproject-demo"
    tester.execute(f"{path}")

    demo_path = app.poetry.file.path.parent.joinpath(path).resolve().as_posix()
    expected = f"""\

Updating dependencies
Resolving dependencies...

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.2 {demo_path})

Writing lock file
"""

    assert tester.io.fetch_output() == expected
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 2


@pytest.mark.parametrize(
    "required_fixtures",
    [["distributions/demo-0.1.0-py2.py3-none-any.whl"]],
)
def test_add_file_constraint_wheel(
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
) -> None:
    repo.add_package(get_package("pendulum", "1.4.4"))

    path = "../distributions/demo-0.1.0-py2.py3-none-any.whl"
    tester.execute(f"{path}")

    demo_path = app.poetry.file.path.parent.joinpath(path).resolve().as_posix()
    expected = f"""\

Updating dependencies
Resolving dependencies...

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.0 {demo_path})

Writing lock file
"""

    assert tester.io.fetch_output() == expected
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 2

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

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
) -> None:
    repo.add_package(get_package("pendulum", "1.4.4"))

    path = "../distributions/demo-0.1.0.tar.gz"
    tester.execute(f"{path}")

    demo_path = app.poetry.file.path.parent.joinpath(path).resolve().as_posix()
    expected = f"""\

Updating dependencies
Resolving dependencies...

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo (0.1.0 {demo_path})

Writing lock file
"""

    assert tester.io.fetch_output() == expected
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 2

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {"path": path}


@pytest.mark.parametrize("extra_name", ["msgpack", "MsgPack"])
def test_add_constraint_with_extras_option(
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
    extra_name: str,
) -> None:
    cachy2 = get_package("cachy", "0.2.0")
    cachy2.extras = {canonicalize_name("msgpack"): [get_dependency("msgpack-python")]}
    msgpack_dep = get_dependency("msgpack-python", ">=0.5 <0.6", optional=True)
    cachy2.add_dependency(msgpack_dep)

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    tester.execute(f"cachy=0.2.0 --extras {extra_name}")

    expected = """\

Updating dependencies
Resolving dependencies...

Package operations: 2 installs, 0 updates, 0 removals

  - Installing msgpack-python (0.5.3)
  - Installing cachy (0.2.0)

Writing lock file
"""

    assert tester.io.fetch_output() == expected
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 2

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

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
) -> None:
    p = mocker.patch("pathlib.Path.cwd")
    p.return_value = Path(__file__) / ".."

    repo.add_package(get_package("pendulum", "1.4.4"))

    tester.execute(
        "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
    )

    expected = """\

Updating dependencies
Resolving dependencies...

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (1.4.4)
  - Installing demo\
 (0.1.0 https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl)

Writing lock file
"""

    assert tester.io.fetch_output() == expected
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 2

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

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
) -> None:
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

Package operations: 4 installs, 0 updates, 0 removals

  - Installing cleo (0.6.5)
  - Installing pendulum (1.4.4)
  - Installing tomlkit (0.5.5)
  - Installing demo\
 (0.1.0 https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl)

Writing lock file
"""
    # Order might be different, split into lines and compare the overall output.
    expected_lines = set(expected.splitlines())
    output = set(tester.io.fetch_output().splitlines())
    assert output == expected_lines
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 4

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

    assert "demo" in content["dependencies"]
    assert content["dependencies"]["demo"] == {
        "url": (
            "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
        ),
        "extras": [extra_name, "bar"],
    }


def test_add_constraint_with_optional(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
) -> None:
    repo.add_package(get_package("cachy", "0.2.0"))
    tester.execute("cachy=0.2.0 --optional")
    expected = """\

Updating dependencies
Resolving dependencies...

No dependencies to install or update

Writing lock file
"""

    assert tester.io.fetch_output() == expected
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 0

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {
        "version": "0.2.0",
        "optional": True,
    }


def test_add_constraint_with_python(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
) -> None:
    cachy2 = get_package("cachy", "0.2.0")

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)

    tester.execute("cachy=0.2.0 --python >=2.7")

    expected = """\

Updating dependencies
Resolving dependencies...

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)

Writing lock file
"""

    assert tester.io.fetch_output() == expected
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 1

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {"version": "0.2.0", "python": ">=2.7"}


def test_add_constraint_with_platform(
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
    env: MockEnv,
) -> None:
    platform = sys.platform
    env._platform = platform

    cachy2 = get_package("cachy", "0.2.0")

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy2)

    tester.execute(f"cachy=0.2.0 --platform {platform} -vvv")

    expected = """\

Updating dependencies
Resolving dependencies...

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)

Writing lock file
"""

    assert tester.io.fetch_output() == expected
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 1

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

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
) -> None:
    repo = LegacyRepository(name="my-index", url="https://my-index.fake")
    package = Package(
        "cachy",
        Version.parse("0.2.0"),
        source_type="legacy",
        source_reference=repo.name,
        source_url=repo._url,
        yanked=False,
    )
    mocker.patch.object(repo, "package", return_value=package)
    mocker.patch.object(repo, "_find_packages", wraps=lambda _, name: [package])

    poetry.pool.add_repository(repo)

    tester.execute("cachy=0.2.0 --source my-index")

    expected = """\

Updating dependencies
Resolving dependencies...

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)

Writing lock file
"""

    assert tester.io.fetch_output() == expected
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 1

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {
        "version": "0.2.0",
        "source": "my-index",
    }


def test_add_constraint_with_source_that_does_not_exist(tester: CommandTester) -> None:
    with pytest.raises(IndexError) as e:
        tester.execute("foo --source i-dont-exist")

    assert str(e.value) == 'Repository "i-dont-exist" does not exist.'


def test_add_constraint_not_found_with_source(
    poetry: Poetry,
    mocker: MockerFixture,
    tester: CommandTester,
) -> None:
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
) -> None:
    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy --group dev")

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)

Writing lock file
"""

    assert tester.io.fetch_output() == expected
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 1

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

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
) -> None:
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

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)

Writing lock file
"""

    assert tester.io.fetch_error() == warning
    assert tester.io.fetch_output() == expected
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 1

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

    assert "cachy" in content["group"]["dev"]["dependencies"]
    assert content["group"]["dev"]["dependencies"]["cachy"] == "^0.2.0"


def test_add_should_not_select_prereleases(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
) -> None:
    repo.add_package(get_package("pyyaml", "3.13"))
    repo.add_package(get_package("pyyaml", "4.2b2"))

    tester.execute("pyyaml")

    expected = """\
Using version ^3.13 for pyyaml

Updating dependencies
Resolving dependencies...

Package operations: 1 install, 0 updates, 0 removals

  - Installing pyyaml (3.13)

Writing lock file
"""

    assert tester.io.fetch_output() == expected
    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 1

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

    assert "pyyaml" in content["dependencies"]
    assert content["dependencies"]["pyyaml"] == "^3.13"


def test_add_should_skip_when_adding_existing_package_with_no_constraint(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
) -> None:
    pyproject: dict[str, Any] = app.poetry.file.read()
    pyproject["tool"]["poetry"]["dependencies"]["foo"] = "^1.0"
    pyproject = cast("TOMLDocument", pyproject)
    app.poetry.file.write(pyproject)

    repo.add_package(get_package("foo", "1.1.2"))
    tester.execute("foo")

    expected = """\
The following packages are already present in the pyproject.toml and will be skipped:

  - foo

If you want to update it to the latest compatible version,\
 you can use `poetry update package`.
If you prefer to upgrade it to the latest available version,\
 you can use `poetry add package@latest`.
"""

    assert expected in tester.io.fetch_output()


def test_add_should_skip_when_adding_canonicalized_existing_package_with_no_constraint(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
) -> None:
    pyproject: dict[str, Any] = app.poetry.file.read()
    pyproject["tool"]["poetry"]["dependencies"]["foo-bar"] = "^1.0"
    pyproject = cast("TOMLDocument", pyproject)
    app.poetry.file.write(pyproject)

    repo.add_package(get_package("foo-bar", "1.1.2"))
    tester.execute("Foo_Bar")

    expected = """\
The following packages are already present in the pyproject.toml and will be skipped:

  - Foo_Bar

If you want to update it to the latest compatible version,\
 you can use `poetry update package`.
If you prefer to upgrade it to the latest available version,\
 you can use `poetry add package@latest`.
"""

    assert expected in tester.io.fetch_output()


def test_add_should_fail_circular_dependency(
    repo: TestRepository, tester: CommandTester
) -> None:
    repo.add_package(get_package("simple-project", "1.1.2"))
    result = tester.execute("simple-project")

    assert result == 1

    expected = "Cannot add dependency on simple-project to project with the same name."
    assert expected in tester.io.fetch_error()


def test_add_latest_should_not_create_duplicate_keys(
    project_factory: ProjectFactory,
    repo: TestRepository,
    command_tester_factory: CommandTesterFactory,
) -> None:
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
    pyproject: dict[str, Any] = poetry.file.read()

    assert "Foo" in pyproject["tool"]["poetry"]["dependencies"]
    assert pyproject["tool"]["poetry"]["dependencies"]["Foo"] == "^0.6"
    assert "foo" not in pyproject["tool"]["poetry"]["dependencies"]

    tester = command_tester_factory("add", poetry=poetry)
    repo.add_package(get_package("foo", "1.1.2"))
    tester.execute("foo@latest")

    updated_pyproject: dict[str, Any] = poetry.file.read()
    assert "Foo" in updated_pyproject["tool"]["poetry"]["dependencies"]
    assert updated_pyproject["tool"]["poetry"]["dependencies"]["Foo"] == "^1.1.2"
    assert "foo" not in updated_pyproject["tool"]["poetry"]["dependencies"]


def test_add_should_work_when_adding_existing_package_with_latest_constraint(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
) -> None:
    pyproject: dict[str, Any] = app.poetry.file.read()
    pyproject["tool"]["poetry"]["dependencies"]["foo"] = "^1.0"
    pyproject = cast("TOMLDocument", pyproject)
    app.poetry.file.write(pyproject)

    repo.add_package(get_package("foo", "1.1.2"))

    tester.execute("foo@latest")

    expected = """\
Using version ^1.1.2 for foo

Updating dependencies
Resolving dependencies...

Package operations: 1 install, 0 updates, 0 removals

  - Installing foo (1.1.2)

Writing lock file
"""

    assert expected in tester.io.fetch_output()

    pyproject2: dict[str, Any] = app.poetry.file.read()
    content = pyproject2["tool"]["poetry"]

    assert "foo" in content["dependencies"]
    assert content["dependencies"]["foo"] == "^1.1.2"


def test_add_chooses_prerelease_if_only_prereleases_are_available(
    repo: TestRepository, tester: CommandTester
) -> None:
    repo.add_package(get_package("foo", "1.2.3b0"))
    repo.add_package(get_package("foo", "1.2.3b1"))

    tester.execute("foo")

    expected = """\
Using version ^1.2.3b1 for foo

Updating dependencies
Resolving dependencies...

Package operations: 1 install, 0 updates, 0 removals

  - Installing foo (1.2.3b1)

Writing lock file
"""
    assert expected in tester.io.fetch_output()


def test_add_prefers_stable_releases(
    repo: TestRepository, tester: CommandTester
) -> None:
    repo.add_package(get_package("foo", "1.2.3"))
    repo.add_package(get_package("foo", "1.2.4b1"))

    tester.execute("foo")

    expected = """\
Using version ^1.2.3 for foo

Updating dependencies
Resolving dependencies...

Package operations: 1 install, 0 updates, 0 removals

  - Installing foo (1.2.3)

Writing lock file
"""

    assert expected in tester.io.fetch_output()


def test_add_with_lock(
    app: PoetryTestApplication, repo: TestRepository, tester: CommandTester
) -> None:
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


def test_add_to_section_that_does_no_exist_yet(
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
) -> None:
    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("cachy --group dev")

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...

Package operations: 1 install, 0 updates, 0 removals

  - Installing cachy (0.2.0)

Writing lock file
"""

    assert tester.io.fetch_output() == expected

    assert isinstance(tester.command, InstallerCommand)
    assert tester.command.installer.executor.installations_count == 1

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

    assert "cachy" in content["group"]["dev"]["dependencies"]
    assert content["group"]["dev"]["dependencies"]["cachy"] == "^0.2.0"


def test_add_keyboard_interrupt_restore_content(
    poetry_with_up_to_date_lockfile: Poetry,
    repo: TestRepository,
    command_tester_factory: CommandTesterFactory,
    mocker: MockerFixture,
) -> None:
    tester = command_tester_factory("add", poetry=poetry_with_up_to_date_lockfile)

    mocker.patch(
        "poetry.installation.installer.Installer._execute",
        side_effect=KeyboardInterrupt(),
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
) -> None:
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


def test_add_should_not_change_lock_file_when_dependency_installation_fail(
    poetry_with_up_to_date_lockfile: Poetry,
    repo: TestRepository,
    command_tester_factory: CommandTesterFactory,
    mocker: MockerFixture,
) -> None:
    tester = command_tester_factory("add", poetry=poetry_with_up_to_date_lockfile)

    repo.add_package(get_package("docker", "4.3.1"))
    repo.add_package(get_package("cachy", "0.2.0"))

    original_pyproject_content = poetry_with_up_to_date_lockfile.file.read()
    original_lockfile_content = poetry_with_up_to_date_lockfile.locker.lock_data

    def error(_: Any) -> int:
        tester.io.write("\n  BuildError\n\n")
        return 1

    mocker.patch("poetry.installation.installer.Installer._execute", side_effect=error)
    tester.execute("cachy")

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...

  BuildError

"""

    assert poetry_with_up_to_date_lockfile.file.read() == original_pyproject_content
    assert poetry_with_up_to_date_lockfile.locker.lock_data == original_lockfile_content
    assert tester.io.fetch_output() == expected


def test_add_with_path_dependency_no_loopiness(
    poetry_with_path_dependency: Poetry,
    repo: TestRepository,
    command_tester_factory: CommandTesterFactory,
) -> None:
    """https://github.com/python-poetry/poetry/issues/7398"""
    tester = command_tester_factory("add", poetry=poetry_with_path_dependency)

    requests_old = get_package("requests", "2.25.1")
    requests_new = get_package("requests", "2.28.2")

    repo.add_package(requests_old)
    repo.add_package(requests_new)

    with pytest.raises(SolverProblemError):
        tester.execute("requests")


def test_add_extras_are_parsed_and_included(
    app: PoetryTestApplication,
    repo: TestRepository,
    tester: CommandTester,
) -> None:
    msgpack_dep = get_dependency("msgpack-python", ">=0.5 <0.6", optional=True)
    redis_dep = get_dependency("redis", ">=3.3.6 <4.0.0", optional=True)

    cachy = get_package("cachy", "0.2.0")
    cachy.add_dependency(msgpack_dep)
    cachy.add_dependency(redis_dep)
    cachy.extras = {
        canonicalize_name("redis"): [redis_dep],
        canonicalize_name("msgpack"): [msgpack_dep],
    }
    repo.add_package(cachy)

    msgpack = get_package("msgpack-python", "0.5.1")
    repo.add_package(msgpack)

    redis = get_package("redis", "3.4.0")
    repo.add_package(redis)

    tester.execute('cachy --extras "redis msgpack"')

    expected = """\
Using version ^0.2.0 for cachy

Updating dependencies
Resolving dependencies...

Package operations: 3 installs, 0 updates, 0 removals

  - Installing msgpack-python (0.5.1)
  - Installing redis (3.4.0)
  - Installing cachy (0.2.0)

Writing lock file
"""

    assert tester.io.fetch_output() == expected

    pyproject: dict[str, Any] = app.poetry.file.read()
    content = pyproject["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {
        "version": "^0.2.0",
        "extras": ["redis", "msgpack"],
    }


@pytest.mark.parametrize(
    "command",
    [
        "requests --extras security socks",
    ],
)
def test_add_extras_only_accepts_one_package(
    command: str, tester: CommandTester, repo: TestRepository
) -> None:
    """
    You cannot pass in multiple package values to a single --extras flag.\
    e.g. --extras security socks is not allowed.
    """
    repo.add_package(get_package("requests", "2.30.0"))

    with pytest.raises(ValueError) as e:
        tester.execute(command)
        assert (
            str(e.value)
            == "You can only specify one package when using the --extras option"
        )


@pytest.mark.parametrize("command", ["foo", "foo --lock"])
@pytest.mark.parametrize(
    ("locked", "expected_docker"), [(True, "4.3.1"), (False, "4.3.2")]
)
def test_add_does_not_update_locked_dependencies(
    repo: TestRepository,
    poetry_with_up_to_date_lockfile: Poetry,
    tester: CommandTester,
    command_tester_factory: CommandTesterFactory,
    command: str,
    locked: bool,
    expected_docker: str,
) -> None:
    assert isinstance(poetry_with_up_to_date_lockfile.locker, TestLocker)
    poetry_with_up_to_date_lockfile.locker.locked(locked)
    tester = command_tester_factory("add", poetry=poetry_with_up_to_date_lockfile)
    docker_locked = get_package("docker", "4.3.1")
    docker_new = get_package("docker", "4.3.2")
    docker_dep = get_dependency("docker", ">=4.0.0")
    foo = get_package("foo", "0.1.0")
    foo.add_dependency(docker_dep)
    for package in docker_locked, docker_new, foo:
        repo.add_package(package)

    tester.execute(command)

    lock_data = poetry_with_up_to_date_lockfile.locker.lock_data
    docker_locked_after_command = next(
        p for p in lock_data["package"] if p["name"] == "docker"
    )
    assert docker_locked_after_command["version"] == expected_docker
