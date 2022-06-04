from __future__ import annotations

from typing import TYPE_CHECKING

from cleo.exceptions import LogicException
from cleo.loaders.factory_command_loader import FactoryCommandLoader


if TYPE_CHECKING:
    from collections.abc import Callable

    from poetry.console.commands.command import Command


class CommandLoader(FactoryCommandLoader):  # type: ignore[misc]
    def register_factory(
        self, command_name: str, factory: Callable[[], Command]
    ) -> None:
        if command_name in self._factories:
            raise LogicException(f'The command "{command_name}" already exists.')

        self._factories[command_name] = factory
