from typing import Callable

from cleo.exceptions import LogicException
from cleo.loaders.factory_command_loader import FactoryCommandLoader


class CommandLoader(FactoryCommandLoader):
    def register_factory(self, command_name: str, factory: Callable) -> None:
        if command_name in self._factories:
            raise LogicException(f'The command "{command_name}" already exists.')

        self._factories[command_name] = factory
