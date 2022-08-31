from __future__ import annotations

import functools

from typing import TYPE_CHECKING

from poetry.plugins.base_plugin import BasePlugin


if TYPE_CHECKING:
    from poetry.console.application import Application
    from poetry.console.commands.command import Command


class ApplicationPlugin(BasePlugin):
    """
    Base class for application plugins.
    """

    group = "poetry.application.plugin"

    @property
    def commands(self) -> list[type[Command]]:
        return []

    def activate(self, application: Application) -> None:
        def factory(command: type[Command]) -> Command:
            return command()

        for command in self.commands:
            assert command.name is not None

            application.command_loader.register_factory(
                command.name, functools.partial(factory, command)
            )
