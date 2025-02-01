from __future__ import annotations

from pathlib import Path
from typing import Any

from tomlkit.items import Array

from poetry.factory import Factory


def get_self_command_dependencies(locked: bool = True) -> Array:
    from poetry.console.commands.self.self_command import SelfCommand
    from poetry.locations import CONFIG_DIR

    system_pyproject_file = SelfCommand.get_default_system_pyproject_file()

    assert system_pyproject_file.exists()
    assert system_pyproject_file.parent == Path(CONFIG_DIR)

    if locked:
        assert system_pyproject_file.parent.joinpath("poetry.lock").exists()

    poetry = Factory().create_poetry(system_pyproject_file.parent, disable_plugins=True)

    pyproject: dict[str, Any] = poetry.file.read()
    content = pyproject["dependency-groups"]

    assert SelfCommand.ADDITIONAL_PACKAGE_GROUP in content

    dependencies = content[SelfCommand.ADDITIONAL_PACKAGE_GROUP]
    assert isinstance(dependencies, Array)
    return dependencies
