import pytest

from poetry.core.packages.package import Package
from poetry.factory import Factory


@pytest.fixture()
def tester(command_tester_factory):
    return command_tester_factory("plugin add")


def assert_plugin_add_result(tester, app, env, expected, constraint):
    assert tester.io.fetch_output() == expected

    update_command = app.find("update")
    assert update_command.poetry.file.parent == env.path
    assert update_command.poetry.locker.lock.parent == env.path
    assert update_command.poetry.locker.lock.exists()

    content = update_command.poetry.file.read()["tool"]["poetry"]
    assert "poetry-plugin" in content["dependencies"]
    assert content["dependencies"]["poetry-plugin"] == constraint


def test_add_no_constraint(app, repo, tester, env, installed):
    repo.add_package(Package("poetry-plugin", "0.1.0"))

    tester.execute("poetry-plugin")

    expected = """\
Using version ^0.1.0 for poetry-plugin
Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing poetry-plugin (0.1.0)
"""
    assert_plugin_add_result(tester, app, env, expected, "^0.1.0")


def test_add_with_constraint(app, repo, tester, env, installed):
    repo.add_package(Package("poetry-plugin", "0.1.0"))
    repo.add_package(Package("poetry-plugin", "0.2.0"))

    tester.execute("poetry-plugin@^0.2.0")

    expected = """\
Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing poetry-plugin (0.2.0)
"""

    assert_plugin_add_result(tester, app, env, expected, "^0.2.0")


def test_add_with_git_constraint(app, repo, tester, env, installed):
    repo.add_package(Package("pendulum", "2.0.5"))

    tester.execute("git+https://github.com/demo/poetry-plugin.git")

    expected = """\
Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  • Installing pendulum (2.0.5)
  • Installing poetry-plugin (0.1.2 9cf87a2)
"""

    assert_plugin_add_result(
        tester, app, env, expected, {"git": "https://github.com/demo/poetry-plugin.git"}
    )


def test_add_with_git_constraint_with_extras(app, repo, tester, env, installed):
    repo.add_package(Package("pendulum", "2.0.5"))
    repo.add_package(Package("tomlkit", "0.7.0"))

    tester.execute("git+https://github.com/demo/poetry-plugin.git[foo]")

    expected = """\
Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 3 installs, 0 updates, 0 removals

  • Installing pendulum (2.0.5)
  • Installing tomlkit (0.7.0)
  • Installing poetry-plugin (0.1.2 9cf87a2)
"""

    assert_plugin_add_result(
        tester,
        app,
        env,
        expected,
        {
            "git": "https://github.com/demo/poetry-plugin.git",
            "extras": ["foo"],
        },
    )


def test_add_existing_plugin_warns_about_no_operation(
    app, repo, tester, env, installed
):
    env.path.joinpath("pyproject.toml").write_text(
        """\
[tool.poetry]
name = "poetry"
version = "1.2.0"
description = "Python dependency management and packaging made easy."
authors = [
    "Sébastien Eustace <sebastien@eustace.io>"
]

[tool.poetry.dependencies]
python = "^3.6"
poetry-plugin = "^1.2.3"
""",
        encoding="utf-8",
    )

    installed.add_package(Package("poetry-plugin", "1.2.3"))

    repo.add_package(Package("poetry-plugin", "1.2.3"))

    tester.execute("poetry-plugin")

    expected = """\
The following plugins are already present in the pyproject.toml file and will be skipped:

  • poetry-plugin

If you want to update it to the latest compatible version, you can use `poetry plugin update package`.
If you prefer to upgrade it to the latest available version, you can use `poetry plugin add package@latest`.

"""

    assert tester.io.fetch_output() == expected

    update_command = app.find("update")
    # The update command should not have been called
    assert update_command.poetry.file.parent != env.path


def test_add_existing_plugin_updates_if_requested(
    app, repo, tester, env, installed, mocker
):
    env.path.joinpath("pyproject.toml").write_text(
        """\
[tool.poetry]
name = "poetry"
version = "1.2.0"
description = "Python dependency management and packaging made easy."
authors = [
    "Sébastien Eustace <sebastien@eustace.io>"
]

[tool.poetry.dependencies]
python = "^3.6"
poetry-plugin = "^1.2.3"
""",
        encoding="utf-8",
    )

    installed.add_package(Package("poetry-plugin", "1.2.3"))

    repo.add_package(Package("poetry-plugin", "1.2.3"))
    repo.add_package(Package("poetry-plugin", "2.3.4"))

    tester.execute("poetry-plugin@latest")

    expected = """\
Using version ^2.3.4 for poetry-plugin
Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 0 installs, 1 update, 0 removals

  • Updating poetry-plugin (1.2.3 -> 2.3.4)
"""

    assert_plugin_add_result(tester, app, env, expected, "^2.3.4")


def test_adding_a_plugin_can_update_poetry_dependencies_if_needed(
    app, repo, tester, env, installed
):
    poetry_package = Package("poetry", "1.2.0")
    poetry_package.add_dependency(Factory.create_dependency("tomlkit", "^0.7.0"))

    plugin_package = Package("poetry-plugin", "1.2.3")
    plugin_package.add_dependency(Factory.create_dependency("tomlkit", "^0.7.2"))

    installed.add_package(poetry_package)
    installed.add_package(Package("tomlkit", "0.7.1"))

    repo.add_package(plugin_package)
    repo.add_package(Package("tomlkit", "0.7.1"))
    repo.add_package(Package("tomlkit", "0.7.2"))

    tester.execute("poetry-plugin")

    expected = """\
Using version ^1.2.3 for poetry-plugin
Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 1 update, 0 removals

  • Updating tomlkit (0.7.1 -> 0.7.2)
  • Installing poetry-plugin (1.2.3)
"""

    assert_plugin_add_result(tester, app, env, expected, "^1.2.3")
