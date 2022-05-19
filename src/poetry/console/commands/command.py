from __future__ import annotations

import sys

from typing import TYPE_CHECKING
from typing import Any

from cleo.commands.command import Command as BaseCommand
from cleo.exceptions import ValueException


if TYPE_CHECKING:
    from cleo.io.io import IO

    from poetry.console.application import Application
    from poetry.poetry import Poetry


class Command(BaseCommand):  # type: ignore[misc]
    loggers: list[str] = []

    _poetry: Poetry | None = None

    def run(self, io: IO) -> int:
        if io.input.stream is None:
            io.input.set_stream(sys.stdin)
        return super().run(io)

    @property
    def poetry(self) -> Poetry:
        if self._poetry is None:
            return self.get_application().poetry

        return self._poetry

    def set_poetry(self, poetry: Poetry) -> None:
        self._poetry = poetry

    def get_application(self) -> Application:
        application: Application = self.application
        return application

    def reset_poetry(self) -> None:
        self.get_application().reset_poetry()

    def option(self, name: str, default: Any = None) -> Any:
        try:
            return super().option(name)
        except ValueException:
            return default
