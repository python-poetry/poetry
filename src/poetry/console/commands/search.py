from __future__ import annotations

from typing import TYPE_CHECKING
from typing import ClassVar

from cleo.helpers import argument

from poetry.console.commands.command import Command


if TYPE_CHECKING:
    from cleo.io.inputs.argument import Argument


class SearchCommand(Command):
    name = "search"
    description = "Searches for packages on remote repositories."

    arguments: ClassVar[list[Argument]] = [
        argument("tokens", "The tokens to search for.", multiple=True)
    ]

    def handle(self) -> int:
        seen = set()

        for result in self.poetry.pool.search(self.argument("tokens")):
            if result.pretty_string in seen:
                continue

            seen.add(result.pretty_string)

            self.line("")
            name = f"<info>{result.name}</>"

            name += f" (<comment>{result.version}</>)"

            self.line(name)

            if result.description:
                self.line(f" {result.description}")

        return 0
