from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.core.packages.dependency_group import MAIN_GROUP


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry
    from tests.types import CommandTesterFactory
    from tests.types import ProjectFactory


PYPROJECT_CONTENT = """\
[tool.poetry]
name = "test-project"
version = "1.0.0"
description = "Test project"
authors = ["Test Author <test@example.com>"]

[tool.poetry.dependencies]
python = "^3.8"
requests = "^2.0.0"

[tool.poetry.group.test.dependencies]
pytest = "^7.0.0"

[tool.poetry.group.dev.dependencies]
black = "^23.0.0"

[tool.poetry.group.docs]
optional = true

[tool.poetry.group.docs.dependencies]
sphinx = "^5.0.0"
"""


@pytest.fixture
def poetry(project_factory: ProjectFactory) -> Poetry:
    return project_factory(
        name="test-default-group-optionality", pyproject_content=PYPROJECT_CONTENT
    )


@pytest.fixture
def install_tester(
    command_tester_factory: CommandTesterFactory, poetry: Poetry
) -> CommandTester:
    return command_tester_factory("install")


@pytest.fixture
def config_tester(
    command_tester_factory: CommandTesterFactory, poetry: Poetry
) -> CommandTester:
    return command_tester_factory("config")


def test_default_behavior_without_config(
    install_tester: CommandTester, mocker: MockerFixture
) -> None:
    """
    By default, without the config set, all non-optional groups are installed.
    """
    mocker.patch.object(install_tester.command.installer, "run", return_value=0)
    mocker.patch(
        "poetry.masonry.builders.editable.EditableBuilder",
        side_effect=Exception("Should not be called"),
    )

    status_code = install_tester.execute("--no-root")
    assert status_code == 0

    # By default, main, test, and dev should be installed (not docs as it's optional)
    installer_groups = set(install_tester.command.installer._groups or [])
    assert installer_groups == {MAIN_GROUP, "test", "dev"}


def test_with_default_group_optionality_enabled(
    config_tester: CommandTester,
    install_tester: CommandTester,
    mocker: MockerFixture,
) -> None:
    """
    With default-group-optionality enabled, only main group is installed by default.
    """
    # Enable the configuration
    config_tester.execute("--local default-group-optionality true")
    assert config_tester.status_code == 0

    # Reload config
    install_tester.command.poetry.config.merge({"default-group-optionality": True})

    mocker.patch.object(install_tester.command.installer, "run", return_value=0)
    mocker.patch(
        "poetry.masonry.builders.editable.EditableBuilder",
        side_effect=Exception("Should not be called"),
    )

    status_code = install_tester.execute("--no-root")
    assert status_code == 0

    # With default-group-optionality, only main group should be installed
    installer_groups = set(install_tester.command.installer._groups or [])
    assert installer_groups == {MAIN_GROUP}


def test_with_default_group_optionality_and_with_option(
    install_tester: CommandTester, mocker: MockerFixture
) -> None:
    """
    With default-group-optionality enabled, --with can explicitly include groups.
    """
    # Enable the configuration
    install_tester.command.poetry.config.merge({"default-group-optionality": True})

    mocker.patch.object(install_tester.command.installer, "run", return_value=0)
    mocker.patch(
        "poetry.masonry.builders.editable.EditableBuilder",
        side_effect=Exception("Should not be called"),
    )

    status_code = install_tester.execute("--no-root --with test,dev")
    assert status_code == 0

    # Should install main, test, and dev groups
    installer_groups = set(install_tester.command.installer._groups or [])
    assert installer_groups == {MAIN_GROUP, "test", "dev"}


def test_with_default_group_optionality_and_only_option(
    install_tester: CommandTester, mocker: MockerFixture
) -> None:
    """
    With default-group-optionality enabled, --only still works as expected.
    """
    # Enable the configuration
    install_tester.command.poetry.config.merge({"default-group-optionality": True})

    mocker.patch.object(install_tester.command.installer, "run", return_value=0)
    mocker.patch(
        "poetry.masonry.builders.editable.EditableBuilder",
        side_effect=Exception("Should not be called"),
    )

    status_code = install_tester.execute("--no-root --only test")
    assert status_code == 0

    # Should only install test group
    installer_groups = set(install_tester.command.installer._groups or [])
    assert installer_groups == {"test"}


def test_config_get_default_group_optionality(config_tester: CommandTester) -> None:
    """
    Test getting the default-group-optionality configuration value.
    """
    config_tester.execute("default-group-optionality")
    assert config_tester.status_code == 0
    assert "false" in config_tester.io.fetch_output().strip().lower()


def test_config_set_default_group_optionality(config_tester: CommandTester) -> None:
    """
    Test setting the default-group-optionality configuration value.
    """
    config_tester.execute("--local default-group-optionality true")
    assert config_tester.status_code == 0

    config_tester.io.clear_output()
    config_tester.execute("--local default-group-optionality")
    assert config_tester.status_code == 0
    assert "true" in config_tester.io.fetch_output().strip().lower()


def test_config_unset_default_group_optionality(config_tester: CommandTester) -> None:
    """
    Test unsetting the default-group-optionality configuration value.
    """
    config_tester.execute("--local default-group-optionality true")
    assert config_tester.status_code == 0

    config_tester.execute("--local default-group-optionality --unset")
    assert config_tester.status_code == 0

    config_tester.io.clear_output()
    config_tester.execute("default-group-optionality")
    assert config_tester.status_code == 0
    # Should revert to default (false)
    assert "false" in config_tester.io.fetch_output().strip().lower()


def test_backward_compatibility(
    install_tester: CommandTester, mocker: MockerFixture
) -> None:
    """
    Test that existing behavior is maintained when config is not set.
    """
    mocker.patch.object(install_tester.command.installer, "run", return_value=0)
    mocker.patch(
        "poetry.masonry.builders.editable.EditableBuilder",
        side_effect=Exception("Should not be called"),
    )

    # Without setting the config, behavior should be unchanged
    status_code = install_tester.execute("--no-root")
    assert status_code == 0

    installer_groups = set(install_tester.command.installer._groups or [])
    # test and dev should be included by default (not docs since it's optional)
    assert installer_groups == {MAIN_GROUP, "test", "dev"}
