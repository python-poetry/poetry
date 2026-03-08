from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import cast

import pytest
import tomlkit

from poetry.core.packages.dependency_group import DependencyGroup
from poetry.core.packages.package import Package

from poetry.factory import Factory
from tests.helpers import TestLocker
from tests.helpers import get_package


if TYPE_CHECKING:
    from collections.abc import Callable

    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture
    from tomlkit import TOMLDocument

    from poetry.poetry import Poetry
    from poetry.repositories import Repository
    from tests.helpers import PoetryTestApplication
    from tests.helpers import TestRepository
    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter
    from tests.types import ProjectFactory


@pytest.fixture
def poetry_with_up_to_date_lockfile(
    project_factory: ProjectFactory, fixture_dir: FixtureDirGetter
) -> Callable[[str], Poetry]:
    def get_poetry(fixture_name: str) -> Poetry:
        source = fixture_dir(fixture_name)

        poetry = project_factory(
            name="foobar",
            pyproject_content=(source / "pyproject.toml").read_text(encoding="utf-8"),
            poetry_lock_content=(source / "poetry.lock").read_text(encoding="utf-8"),
        )

        assert isinstance(poetry.locker, TestLocker)
        poetry.locker.locked(True)
        return poetry

    return get_poetry


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("remove")


def test_remove_from_project_and_poetry(
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    installed: Repository,
) -> None:
    repo.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("bar", "1.0.0"))

    pyproject: dict[str, Any] = app.poetry.file.read()

    project_dependencies: dict[str, Any] = tomlkit.parse(
        """\
[project]
dependencies = [
    "foo>=2.0",
    "bar>=1.0",
]
"""
    )

    poetry_dependencies: dict[str, Any] = tomlkit.parse(
        """\
[tool.poetry.dependencies]
foo = "^2.0.0"
bar = "^1.0.0"

"""
    )

    pyproject["project"]["dependencies"] = project_dependencies["project"][
        "dependencies"
    ]
    pyproject["tool"]["poetry"]["dependencies"] = poetry_dependencies["tool"]["poetry"][
        "dependencies"
    ]
    pyproject = cast("TOMLDocument", pyproject)
    app.poetry.file.write(pyproject)

    app.poetry.package.add_dependency(Factory.create_dependency("foo", "^2.0.0"))
    app.poetry.package.add_dependency(Factory.create_dependency("bar", "^1.0.0"))

    tester.execute("foo")

    pyproject = app.poetry.file.read()
    pyproject = cast("dict[str, Any]", pyproject)
    project_dependencies = pyproject["project"]["dependencies"]
    assert "foo>=2.0" not in project_dependencies
    assert "bar>=1.0" in project_dependencies
    poetry_dependencies = pyproject["tool"]["poetry"]["dependencies"]
    assert "foo" not in poetry_dependencies
    assert "bar" in poetry_dependencies

    expected_project_string = """\
dependencies = [
    "bar>=1.0",
]
"""
    expected_poetry_string = """\

[tool.poetry.dependencies]
bar = "^1.0.0"

"""
    pyproject = cast("TOMLDocument", pyproject)
    string_content = pyproject.as_string()
    if "\r\n" in string_content:
        # consistent line endings
        expected_project_string = expected_project_string.replace("\n", "\r\n")
        expected_poetry_string = expected_poetry_string.replace("\n", "\r\n")

    assert expected_project_string in string_content
    assert expected_poetry_string in string_content


def test_remove_from_pep735_group_and_poetry_group(
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    installed: Repository,
) -> None:
    repo.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("bar", "1.0.0"))

    pyproject: dict[str, Any] = app.poetry.file.read()

    pep735_dependencies: dict[str, Any] = tomlkit.parse(
        """\
[dependency-groups]
dev = [
    "foo>=2.0",
    "bar>=1.0",
]
"""
    )

    poetry_dependencies: dict[str, Any] = tomlkit.parse(
        """\
[tool.poetry.group.dev.dependencies]
foo = "^2.0.0"
bar = "^1.0.0"

"""
    )

    pyproject["dependency-groups"] = pep735_dependencies["dependency-groups"]
    pyproject["tool"]["poetry"]["group"] = poetry_dependencies["tool"]["poetry"][
        "group"
    ]
    pyproject = cast("TOMLDocument", pyproject)
    app.poetry.file.write(pyproject)

    app.poetry.package.add_dependency(
        Factory.create_dependency("foo", "^2.0.0", groups=["dev"])
    )
    app.poetry.package.add_dependency(
        Factory.create_dependency("bar", "^1.0.0", groups=["dev"])
    )

    tester.execute("foo")

    pyproject = app.poetry.file.read()
    pyproject = cast("dict[str, Any]", pyproject)
    pep735_dependencies = pyproject["dependency-groups"]["dev"]
    assert "foo>=2.0" not in pep735_dependencies
    assert "bar>=1.0" in pep735_dependencies
    poetry_dependencies = pyproject["tool"]["poetry"]["group"]["dev"]["dependencies"]
    assert "foo" not in poetry_dependencies
    assert "bar" in poetry_dependencies

    expected_pep735_string = """\
[dependency-groups]
dev = [
    "bar>=1.0",
]
"""
    expected_poetry_string = """\

[tool.poetry.group.dev.dependencies]
bar = "^1.0.0"

"""
    pyproject = cast("TOMLDocument", pyproject)
    string_content = pyproject.as_string()
    if "\r\n" in string_content:
        # consistent line endings
        expected_pep735_string = expected_pep735_string.replace("\n", "\r\n")
        expected_poetry_string = expected_poetry_string.replace("\n", "\r\n")

    assert expected_pep735_string in string_content
    assert expected_poetry_string in string_content


@pytest.mark.parametrize("pep_735", [True, False])
def test_remove_without_specific_group_removes_from_all_groups(
    pep_735: bool,
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    installed: Repository,
) -> None:
    """
    Removing without specifying a group removes packages from all groups.
    """
    installed.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("baz", "1.0.0"))

    pyproject: dict[str, Any] = app.poetry.file.read()
    pyproject["tool"]["poetry"]["dependencies"]["foo"] = "^2.0.0"

    if pep_735:
        groups_content: dict[str, Any] = tomlkit.parse(
            """\
[dependency-groups]
bar = [
    "foo (>=2.0,<3.0)",
    "baz (>=1.0,<2.0)",
]
"""
        )
        pyproject["dependency-groups"] = groups_content["dependency-groups"]

    else:
        groups_content = tomlkit.parse(
            """\
[tool.poetry.group.bar.dependencies]
foo = "^2.0.0"
baz = "^1.0.0"

"""
        )
        groups_content = cast("dict[str, Any]", groups_content)
        pyproject["tool"]["poetry"]["group"] = groups_content["tool"]["poetry"]["group"]

    pyproject = cast("TOMLDocument", pyproject)
    app.poetry.file.write(pyproject)

    app.poetry.package.add_dependency(Factory.create_dependency("foo", "^2.0.0"))
    app.poetry.package.add_dependency(
        Factory.create_dependency("foo", "^2.0.0", groups=["bar"])
    )
    app.poetry.package.add_dependency(
        Factory.create_dependency("baz", "^1.0.0", groups=["bar"])
    )

    tester.execute("foo")

    pyproject = app.poetry.file.read()
    pyproject = cast("dict[str, Any]", pyproject)
    content = pyproject["tool"]["poetry"]
    assert "foo" not in content["dependencies"]

    if pep_735:
        assert not any("foo" in dep for dep in pyproject["dependency-groups"]["bar"])
        assert any("baz" in dep for dep in pyproject["dependency-groups"]["bar"])
        expected = """\
[dependency-groups]
bar = [
    "baz (>=1.0,<2.0)",
]
"""
    else:
        assert "foo" not in content["group"]["bar"]["dependencies"]
        assert "baz" in content["group"]["bar"]["dependencies"]

        expected = """\
[tool.poetry.group.bar.dependencies]
baz = "^1.0.0"
"""
    pyproject = cast("TOMLDocument", pyproject)
    string_content = pyproject.as_string()
    if "\r\n" in string_content:
        # consistent line endings
        expected = expected.replace("\n", "\r\n")

    assert expected in string_content


@pytest.mark.parametrize("pep_735", [True, False])
def test_remove_with_specific_group_removes_from_specific_groups(
    pep_735: bool,
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    installed: Repository,
) -> None:
    """
    Removing with a specific group given removes packages only from this group.
    """
    installed.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("baz", "1.0.0"))

    pyproject: dict[str, Any] = app.poetry.file.read()
    pyproject["tool"]["poetry"]["dependencies"]["foo"] = "^2.0.0"

    if pep_735:
        groups_content: dict[str, Any] = tomlkit.parse(
            """\
[dependency-groups]
bar = [
    "foo (>=2.0,<3.0)",
    "baz (>=1.0,<2.0)",
]
    """
        )
        pyproject["dependency-groups"] = groups_content["dependency-groups"]

    else:
        groups_content = tomlkit.parse(
            """\
[tool.poetry.group.bar.dependencies]
foo = "^2.0.0"
baz = "^1.0.0"
    """
        )
        groups_content = cast("dict[str, Any]", groups_content)
        pyproject["tool"]["poetry"]["group"] = groups_content["tool"]["poetry"]["group"]

    pyproject = cast("TOMLDocument", pyproject)
    app.poetry.file.write(pyproject)

    app.poetry.package.add_dependency(Factory.create_dependency("foo", "^2.0.0"))
    app.poetry.package.add_dependency(
        Factory.create_dependency("foo", "^2.0.0", groups=["bar"])
    )
    app.poetry.package.add_dependency(
        Factory.create_dependency("baz", "^1.0.0", groups=["bar"])
    )

    tester.execute("foo --group bar")

    pyproject = app.poetry.file.read()
    pyproject = cast("dict[str, Any]", pyproject)
    content = pyproject["tool"]["poetry"]
    assert "foo" in content["dependencies"]

    if pep_735:
        assert not any("foo" in dep for dep in pyproject["dependency-groups"]["bar"])
        assert any("baz" in dep for dep in pyproject["dependency-groups"]["bar"])
        expected = """\
[dependency-groups]
bar = [
    "baz (>=1.0,<2.0)",
]
"""
    else:
        assert "foo" not in content["group"]["bar"]["dependencies"]
        assert "baz" in content["group"]["bar"]["dependencies"]

        expected = """\
[tool.poetry.group.bar.dependencies]
baz = "^1.0.0"
"""
    pyproject = cast("TOMLDocument", pyproject)
    string_content = pyproject.as_string()
    if "\r\n" in string_content:
        # consistent line endings
        expected = expected.replace("\n", "\r\n")

    assert expected in string_content


@pytest.mark.parametrize("pep_735", [True, False])
def test_remove_does_not_keep_empty_groups(
    pep_735: bool,
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    installed: Repository,
) -> None:
    """
    Empty groups are automatically discarded after package removal.
    """
    installed.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("baz", "1.0.0"))

    pyproject: dict[str, Any] = app.poetry.file.read()
    pyproject["tool"]["poetry"]["dependencies"]["foo"] = "^2.0.0"

    if pep_735:
        groups_content: dict[str, Any] = tomlkit.parse(
            """\
[dependency-groups]
bar = [
    "foo (>=2.0,<3.0)",
    "baz (>=1.0,<2.0)",
]
    """
        )
        pyproject["dependency-groups"] = groups_content["dependency-groups"]
    else:
        groups_content = tomlkit.parse(
            """\
[tool.poetry.group.bar.dependencies]
foo = "^2.0.0"
baz = "^1.0.0"

"""
        )
        groups_content = cast("dict[str, Any]", groups_content)
        pyproject["tool"]["poetry"]["group"] = groups_content["tool"]["poetry"]["group"]
    pyproject = cast("TOMLDocument", pyproject)
    app.poetry.file.write(pyproject)

    app.poetry.package.add_dependency(Factory.create_dependency("foo", "^2.0.0"))
    app.poetry.package.add_dependency(
        Factory.create_dependency("foo", "^2.0.0", groups=["bar"])
    )
    app.poetry.package.add_dependency(
        Factory.create_dependency("baz", "^1.0.0", groups=["bar"])
    )

    tester.execute("foo baz --group bar")

    pyproject = app.poetry.file.read()
    pyproject = cast("dict[str, Any]", pyproject)
    content = pyproject["tool"]["poetry"]

    assert "foo" in content["dependencies"]

    if pep_735:
        assert "bar" not in pyproject.get("dependency-groups", {})
        assert "dependency-groups" not in pyproject
    else:
        # The group 'bar' should be removed entirely from the configuration
        assert "group" not in content
        content = cast("TOMLDocument", content)
        assert "[tool.poetry.group.bar]" not in content.as_string()
        assert "[tool.poetry.group]" not in content.as_string()


@pytest.mark.parametrize("pep_735", [True, False])
def test_remove_canonicalized_named_removes_dependency_correctly(
    pep_735: bool,
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    installed: Repository,
) -> None:
    """
    Removing a dependency using a canonicalized named removes the dependency.
    """
    installed.add_package(Package("foo-bar", "2.0.0"))
    repo.add_package(Package("foo-bar", "2.0.0"))
    repo.add_package(Package("baz", "1.0.0"))

    pyproject: dict[str, Any] = app.poetry.file.read()
    pyproject["tool"]["poetry"]["dependencies"]["foo-bar"] = "^2.0.0"

    if pep_735:
        groups_content: dict[str, Any] = tomlkit.parse(
            """\
[dependency-groups]
bar = [
    "foo-bar (>=2.0,<3.0)",
    "baz (>=1.0,<2.0)",
]
"""
        )
        pyproject["dependency-groups"] = groups_content["dependency-groups"]
    else:
        groups_content = tomlkit.parse(
            """\
[tool.poetry.group.bar.dependencies]
foo-bar = "^2.0.0"
baz = "^1.0.0"

"""
        )
        groups_content = cast("dict[str, Any]", groups_content)
        pyproject["tool"]["poetry"].value._insert_after(
            "dependencies", "group", groups_content["tool"]["poetry"]["group"]
        )
    pyproject = cast("TOMLDocument", pyproject)
    app.poetry.file.write(pyproject)

    app.poetry.package.add_dependency(Factory.create_dependency("foo-bar", "^2.0.0"))
    app.poetry.package.add_dependency(
        Factory.create_dependency("foo-bar", "^2.0.0", groups=["bar"])
    )
    app.poetry.package.add_dependency(
        Factory.create_dependency("baz", "^1.0.0", groups=["bar"])
    )

    tester.execute("Foo_Bar")

    pyproject = app.poetry.file.read()
    pyproject = cast("dict[str, Any]", pyproject)
    content = pyproject["tool"]["poetry"]

    assert "foo-bar" not in content["dependencies"]

    if pep_735:
        assert not any("foo" in dep for dep in pyproject["dependency-groups"]["bar"])
        assert any("baz" in dep for dep in pyproject["dependency-groups"]["bar"])
        expected = """\
[dependency-groups]
bar = [
    "baz (>=1.0,<2.0)",
]
"""
    else:
        assert "foo-bar" not in content["group"]["bar"]["dependencies"]
        assert "baz" in content["group"]["bar"]["dependencies"]

        expected = """\
[tool.poetry.group.bar.dependencies]
baz = "^1.0.0"
"""
    pyproject = cast("TOMLDocument", pyproject)
    string_content = pyproject.as_string()
    if "\r\n" in string_content:
        # consistent line endings
        expected = expected.replace("\n", "\r\n")

    assert expected in string_content


def test_remove_package_does_not_exist(
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    command_tester_factory: CommandTesterFactory,
) -> None:
    repo.add_package(Package("foo", "2.0.0"))

    original_content = app.poetry.file.read().as_string()

    with pytest.raises(ValueError) as e:
        tester.execute("foo")

    assert str(e.value) == "The following packages were not found: foo"
    assert app.poetry.file.read().as_string() == original_content


def test_remove_package_no_dependencies(
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    command_tester_factory: CommandTesterFactory,
) -> None:
    repo.add_package(Package("foo", "2.0.0"))

    pyproject: dict[str, Any] = app.poetry.file.read()
    assert "dependencies" not in pyproject["project"]
    del pyproject["tool"]["poetry"]["dependencies"]
    pyproject = cast("TOMLDocument", pyproject)
    app.poetry.file.write(pyproject)
    app.poetry.package._dependency_groups = {}

    with pytest.raises(ValueError) as e:
        tester.execute("foo")

    assert str(e.value) == "The following packages were not found: foo"


def test_remove_command_should_not_write_changes_upon_installer_errors(
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    command_tester_factory: CommandTesterFactory,
    mocker: MockerFixture,
) -> None:
    repo.add_package(Package("foo", "2.0.0"))

    command_tester_factory("add").execute("foo")

    mocker.patch("poetry.installation.installer.Installer.run", return_value=1)

    original_content = app.poetry.file.read().as_string()

    tester.execute("foo")

    assert app.poetry.file.read().as_string() == original_content


@pytest.mark.parametrize(
    "fixture_name", ["up_to_date_lock", "up_to_date_lock_non_package"]
)
def test_remove_with_dry_run_keep_files_intact(
    fixture_name: str,
    poetry_with_up_to_date_lockfile: Callable[[str], Poetry],
    repo: TestRepository,
    command_tester_factory: CommandTesterFactory,
) -> None:
    poetry = poetry_with_up_to_date_lockfile(fixture_name)
    tester = command_tester_factory("remove", poetry=poetry)

    original_pyproject_content = poetry.file.read()
    original_lockfile_content = poetry._locker.lock_data

    repo.add_package(get_package("docker", "4.3.1"))

    tester.execute("docker --dry-run")

    assert poetry.file.read() == original_pyproject_content
    assert poetry._locker.lock_data == original_lockfile_content


@pytest.mark.parametrize(
    "fixture_name", ["up_to_date_lock", "up_to_date_lock_non_package"]
)
def test_remove_performs_uninstall_op(
    fixture_name: str,
    poetry_with_up_to_date_lockfile: Callable[[str], Poetry],
    command_tester_factory: CommandTesterFactory,
    installed: Repository,
) -> None:
    installed.add_package(get_package("docker", "4.3.1"))
    poetry = poetry_with_up_to_date_lockfile(fixture_name)
    tester = command_tester_factory("remove", poetry=poetry)

    tester.execute("docker")

    expected = """\
Updating dependencies
Resolving dependencies...

Package operations: 0 installs, 0 updates, 1 removal

  - Removing docker (4.3.1)

Writing lock file
"""

    assert tester.io.fetch_output() == expected


@pytest.mark.parametrize(
    "fixture_name", ["up_to_date_lock", "up_to_date_lock_non_package"]
)
def test_remove_with_lock_does_not_perform_uninstall_op(
    fixture_name: str,
    poetry_with_up_to_date_lockfile: Callable[[str], Poetry],
    command_tester_factory: CommandTesterFactory,
    installed: Repository,
) -> None:
    installed.add_package(get_package("docker", "4.3.1"))
    poetry = poetry_with_up_to_date_lockfile(fixture_name)
    tester = command_tester_factory("remove", poetry=poetry)

    tester.execute("docker --lock")

    expected = """\
Updating dependencies
Resolving dependencies...

Writing lock file
"""

    assert tester.io.fetch_output() == expected


@pytest.mark.parametrize("pep_735", [True, False])
def test_remove_from_nested_pep735_group_and_poetry_group(
    pep_735: bool,
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    installed: Repository,
) -> None:
    """
    Test removing packages from nested dependency groups with `include-group`(pep735) or `include-groups`(poetry).
    """
    installed.add_package(Package("foo", "2.0.0"))
    installed.add_package(Package("baz", "1.0.0"))
    repo.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("baz", "1.0.0"))

    pyproject: dict[str, Any] = app.poetry.file.read()
    pyproject["tool"]["poetry"]["dependencies"]["foo"] = "^2.0.0"

    if pep_735:
        groups_content: dict[str, Any] = tomlkit.parse(
            """\
[dependency-groups]
bar = [
    "foo (>=2.0,<3.0)",
]
foobar = [
    { include-group = "bar" },
    "baz (>=1.0,<2.0)",
]
"""
        )
        pyproject["dependency-groups"] = groups_content["dependency-groups"]

    else:
        groups_content = tomlkit.parse(
            """\
[tool.poetry.group.bar.dependencies]
foo = "^2.0.0"

[tool.poetry.group.foobar]
include-groups = [
    "bar",
]

[tool.poetry.group.foobar.dependencies]
baz = "^1.0.0"
"""
        )
        groups_content = cast("dict[str, Any]", groups_content)
        pyproject["tool"]["poetry"]["group"] = groups_content["tool"]["poetry"]["group"]
    pyproject = cast("TOMLDocument", pyproject)
    app.poetry.file.write(pyproject)

    app.poetry.package.add_dependency(Factory.create_dependency("foo", "^2.0.0"))
    app.poetry.package.add_dependency(
        Factory.create_dependency("foo", "^2.0.0", groups=["bar"])
    )
    app.poetry.package.add_dependency(
        Factory.create_dependency("baz", "^1.0.0", groups=["foobar"])
    )

    tester.execute("baz")

    pyproject = app.poetry.file.read()
    pyproject = cast("dict[str, Any]", pyproject)
    content = pyproject["tool"]["poetry"]

    if pep_735:
        assert "baz" not in pyproject["dependency-groups"]["foobar"]
        assert any(
            isinstance(item, dict) and item.get("include-group") == "bar"
            for item in pyproject["dependency-groups"]["foobar"]
        )
        expected = """\
[dependency-groups]
bar = [
    "foo (>=2.0,<3.0)",
]
foobar = [
    { include-group = "bar" },
]
"""
    else:
        # This also checks that the include-groups section is not removed even if its explicit dependencies are empty
        assert "dependencies" not in content["group"]["foobar"]
        expected = """\
[tool.poetry.group.bar.dependencies]
foo = "^2.0.0"

[tool.poetry.group.foobar]
include-groups = [
    "bar",
]
"""
    pyproject = cast("TOMLDocument", pyproject)
    string_content = pyproject.as_string()
    if "\r\n" in string_content:
        # consistent line endings
        expected = expected.replace("\n", "\r\n")

    assert expected in string_content


@pytest.mark.parametrize("pep_735", [True, False])
@pytest.mark.parametrize("args", ["", " --group bar"])
def test_remove_group_cleans_up_include_group_references(
    pep_735: bool,
    args: str,
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    installed: Repository,
) -> None:
    """
    When a group is removed, any `include-group` references to it in other
    groups should also be cleaned up.
    """
    installed.add_package(Package("foo", "2.0.0"))
    installed.add_package(Package("baz", "1.0.0"))
    repo.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("baz", "1.0.0"))

    pyproject: dict[str, Any] = app.poetry.file.read()

    if pep_735:
        groups_content: dict[str, Any] = tomlkit.parse(
            """\
[dependency-groups]
bar = [
    "foo (>=2.0,<3.0)",
]
foobar = [
    { include-group = "bar" },
]
foobar2 = [
    "baz (>=1.0)",
    { include-group = "bar" },
    "baz (<=3.0)",
]
foobar3 = [
    { include-group = "bar" },
    { include-group = "foobar2" },
]
"""
        )
        pyproject["dependency-groups"] = groups_content["dependency-groups"]
    else:
        groups_content = tomlkit.parse(
            """\
[tool.poetry.group.bar.dependencies]
foo = "^2.0.0"

[tool.poetry.group.foobar]
include-groups = [
    "bar",
]

[tool.poetry.group.foobar2]
include-groups = [
    "bar",
]

[tool.poetry.group.foobar2.dependencies]
baz = "(>=1.0,<=3.0)"

[tool.poetry.group.foobar3]
include-groups = [
    "bar",
    "foobar2",
]
"""
        )
        groups_content = cast("dict[str, Any]", groups_content)
        pyproject["tool"]["poetry"]["group"] = groups_content["tool"]["poetry"]["group"]

    pyproject = cast("TOMLDocument", pyproject)
    app.poetry.file.write(pyproject)

    app.poetry.package.add_dependency(
        Factory.create_dependency("foo", "^2.0.0", groups=["bar"])
    )
    app.poetry.package.add_dependency(
        Factory.create_dependency("baz", "^1.0.0", groups=["foobar2"])
    )
    foobar = DependencyGroup("foobar")
    foobar.include_dependency_group(app.poetry.package.dependency_group("bar"))
    app.poetry.package.add_dependency_group(foobar)
    foobar2 = DependencyGroup("foobar2")
    foobar2.include_dependency_group(app.poetry.package.dependency_group("bar"))
    app.poetry.package.add_dependency_group(foobar2)
    foobar3 = DependencyGroup("foobar3")
    foobar3.include_dependency_group(app.poetry.package.dependency_group("bar"))
    foobar3.include_dependency_group(app.poetry.package.dependency_group("foobar2"))
    app.poetry.package.add_dependency_group(foobar3)

    # Remove all packages from the "bar" group, which should delete the group
    # and also clean up references to it in "foobar"
    tester.execute(f"foo{args}")

    pyproject = app.poetry.file.read()
    pyproject = cast("dict[str, Any]", pyproject)
    content = pyproject["tool"]["poetry"]

    if pep_735:
        # "bar" group should be removed
        assert "bar" not in pyproject.get("dependency-groups", {})
        # "foobar" group should also be removed since it only had include-group
        assert "foobar" not in pyproject.get("dependency-groups", {})
        # "foobar2" should have its include-group cleaned up
        assert "foobar2" in pyproject.get("dependency-groups", {})
        assert pyproject["dependency-groups"]["foobar2"] == [
            "baz (>=1.0)",
            "baz (<=3.0)",
        ]
        # "foobar3" should have its include-groups cleaned up
        assert "foobar3" in pyproject.get("dependency-groups", {})
        assert pyproject["dependency-groups"]["foobar3"] == [
            {"include-group": "foobar2"}
        ]
    else:
        # "bar" group should be removed
        assert "bar" not in content.get("group", {})
        # "foobar" group should also be removed since it only had include-group
        assert "foobar" not in content.get("group", {})
        # "foobar2" should have its include-groups cleaned up
        assert "foobar2" in content.get("group", {})
        assert "include-groups" not in content["group"]["foobar2"]
        assert "dependencies" in content["group"]["foobar2"]
        assert content["group"]["foobar2"]["dependencies"] == {"baz": "(>=1.0,<=3.0)"}
        # "foobar3" should have its include-groups cleaned up
        assert "foobar3" in content.get("group", {})
        assert "include-groups" in content["group"]["foobar3"]
        assert content["group"]["foobar3"]["include-groups"] == ["foobar2"]


def test_remove_optional_dependency_from_project(
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    installed: Repository,
) -> None:
    """Regression test for #10703: cannot remove optional dependency."""
    repo.add_package(Package("pylint", "3.0.0"))
    repo.add_package(Package("bar", "1.0.0"))

    pyproject: dict[str, Any] = app.poetry.file.read()

    optional_deps: dict[str, Any] = tomlkit.parse(
        """\
[project.optional-dependencies]
linting = [
    "pylint>=3.0",
]
"""
    )

    pyproject["project"]["optional-dependencies"] = optional_deps["project"][
        "optional-dependencies"
    ]
    pyproject = cast("TOMLDocument", pyproject)
    app.poetry.file.write(pyproject)

    app.poetry.package.add_dependency(Factory.create_dependency("pylint", ">=3.0"))

    tester.execute("pylint")

    pyproject = app.poetry.file.read()
    pyproject = cast("dict[str, Any]", pyproject)
    assert "optional-dependencies" not in pyproject.get(
        "project", {}
    ) or "pylint" not in str(
        pyproject["project"].get("optional-dependencies", {})
    )


def test_remove_optional_dependency_from_poetry_extras(
    tester: CommandTester,
    app: PoetryTestApplication,
    repo: TestRepository,
    installed: Repository,
) -> None:
    """Regression test for #10703: cannot remove optional dependency (legacy format)."""
    repo.add_package(Package("pylint", "3.0.0"))

    pyproject: dict[str, Any] = app.poetry.file.read()

    poetry_deps: dict[str, Any] = tomlkit.parse(
        """\
[tool.poetry.dependencies]
pylint = {version = "^3.0", optional = true}

[tool.poetry.extras]
linting = ["pylint"]
"""
    )

    pyproject["tool"]["poetry"]["dependencies"] = poetry_deps["tool"]["poetry"][
        "dependencies"
    ]
    pyproject["tool"]["poetry"]["extras"] = poetry_deps["tool"]["poetry"]["extras"]
    pyproject = cast("TOMLDocument", pyproject)
    app.poetry.file.write(pyproject)

    app.poetry.package.add_dependency(Factory.create_dependency("pylint", "^3.0"))

    tester.execute("pylint")

    pyproject = app.poetry.file.read()
    pyproject = cast("dict[str, Any]", pyproject)
    poetry_content = pyproject["tool"]["poetry"]
    assert "pylint" not in poetry_content.get("dependencies", {})
    assert "extras" not in poetry_content or "pylint" not in str(
        poetry_content.get("extras", {})
    )
