from __future__ import annotations

from pathlib import Path
from typing import Any

from tomlkit.items import Table as TOMLTable

from poetry.factory import Factory


def get_self_command_dependencies(locked: bool = True) -> TOMLTable:
    from poetry.console.commands.self.self_command import SelfCommand
    from poetry.locations import CONFIG_DIR

    system_pyproject_file = SelfCommand.get_default_system_pyproject_file()

    assert system_pyproject_file.exists()
    assert system_pyproject_file.parent == Path(CONFIG_DIR)

    if locked:
        assert system_pyproject_file.parent.joinpath("poetry.lock").exists()

    poetry = Factory().create_poetry(system_pyproject_file.parent, disable_plugins=True)

    pyproject: dict[str, Any] = poetry.file.read()
    content = pyproject["tool"]["poetry"]

    assert "group" in content
    assert SelfCommand.ADDITIONAL_PACKAGE_GROUP in content["group"]
    assert "dependencies" in content["group"][SelfCommand.ADDITIONAL_PACKAGE_GROUP]

    dependencies = content["group"][SelfCommand.ADDITIONAL_PACKAGE_GROUP][
        "dependencies"
    ]
    assert isinstance(dependencies, TOMLTable)
    return dependencies
