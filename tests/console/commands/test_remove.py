import pytest
import tomlkit

from poetry.core.packages.package import Package
from poetry.factory import Factory


@pytest.fixture()
def tester(command_tester_factory):
    return command_tester_factory("remove")


def test_remove_without_specific_group_removes_from_all_groups(
    tester, app, repo, command_tester_factory, installed
):
    """
    Removing without specifying a group removes packages from all groups.
    """
    installed.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("baz", "1.0.0"))

    content = app.poetry.file.read()

    groups_content = tomlkit.parse(
        """\
[tool.poetry.group.bar.dependencies]
foo = "^2.0.0"
baz = "^1.0.0"

"""
    )
    content["tool"]["poetry"]["dependencies"]["foo"] = "^2.0.0"
    content["tool"]["poetry"].value._insert_after(
        "dependencies", "group", groups_content["tool"]["poetry"]["group"]
    )
    app.poetry.file.write(content)

    app.poetry.package.add_dependency(Factory.create_dependency("foo", "^2.0.0"))
    app.poetry.package.add_dependency(
        Factory.create_dependency("foo", "^2.0.0", groups=["bar"])
    )
    app.poetry.package.add_dependency(
        Factory.create_dependency("baz", "^1.0.0", groups=["bar"])
    )

    tester.execute("foo")

    content = app.poetry.file.read()["tool"]["poetry"]
    assert "foo" not in content["dependencies"]
    assert "foo" not in content["group"]["bar"]["dependencies"]
    assert "baz" in content["group"]["bar"]["dependencies"]

    expected = """\

[tool.poetry.group.bar.dependencies]
baz = "^1.0.0"

"""

    assert expected in content.as_string()


def test_remove_without_specific_group_removes_from_specific_groups(
    tester, app, repo, command_tester_factory, installed
):
    """
    Removing with a specific group given removes packages only from this group.
    """
    installed.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("baz", "1.0.0"))

    content = app.poetry.file.read()

    groups_content = tomlkit.parse(
        """\
[tool.poetry.group.bar.dependencies]
foo = "^2.0.0"
baz = "^1.0.0"

"""
    )
    content["tool"]["poetry"]["dependencies"]["foo"] = "^2.0.0"
    content["tool"]["poetry"].value._insert_after(
        "dependencies", "group", groups_content["tool"]["poetry"]["group"]
    )
    app.poetry.file.write(content)

    app.poetry.package.add_dependency(Factory.create_dependency("foo", "^2.0.0"))
    app.poetry.package.add_dependency(
        Factory.create_dependency("foo", "^2.0.0", groups=["bar"])
    )
    app.poetry.package.add_dependency(
        Factory.create_dependency("baz", "^1.0.0", groups=["bar"])
    )

    tester.execute("foo --group bar")

    content = app.poetry.file.read()["tool"]["poetry"]
    assert "foo" in content["dependencies"]
    assert "foo" not in content["group"]["bar"]["dependencies"]
    assert "baz" in content["group"]["bar"]["dependencies"]

    expected = """\

[tool.poetry.group.bar.dependencies]
baz = "^1.0.0"

"""

    assert expected in content.as_string()


def test_remove_does_not_live_empty_groups(
    tester, app, repo, command_tester_factory, installed
):
    """
    Empty groups are automatically discarded after package removal.
    """
    installed.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("foo", "2.0.0"))
    repo.add_package(Package("baz", "1.0.0"))

    content = app.poetry.file.read()

    groups_content = tomlkit.parse(
        """\
[tool.poetry.group.bar.dependencies]
foo = "^2.0.0"
baz = "^1.0.0"

"""
    )
    content["tool"]["poetry"]["dependencies"]["foo"] = "^2.0.0"
    content["tool"]["poetry"].value._insert_after(
        "dependencies", "group", groups_content["tool"]["poetry"]["group"]
    )
    app.poetry.file.write(content)

    app.poetry.package.add_dependency(Factory.create_dependency("foo", "^2.0.0"))
    app.poetry.package.add_dependency(
        Factory.create_dependency("foo", "^2.0.0", groups=["bar"])
    )
    app.poetry.package.add_dependency(
        Factory.create_dependency("baz", "^1.0.0", groups=["bar"])
    )

    tester.execute("foo baz --group bar")

    content = app.poetry.file.read()["tool"]["poetry"]
    assert "foo" in content["dependencies"]
    assert "foo" not in content["group"]["bar"]["dependencies"]
    assert "baz" not in content["group"]["bar"]["dependencies"]
    assert "[tool.poetry.group.bar]" not in content.as_string()
    assert "[tool.poetry.group]" not in content.as_string()


def test_remove_command_should_not_write_changes_upon_installer_errors(
    tester, app, repo, command_tester_factory, mocker
):
    repo.add_package(Package("foo", "2.0.0"))

    command_tester_factory("add").execute("foo")

    mocker.patch("poetry.installation.installer.Installer.run", return_value=1)

    original_content = app.poetry.file.read().as_string()

    tester.execute("foo")

    assert app.poetry.file.read().as_string() == original_content
