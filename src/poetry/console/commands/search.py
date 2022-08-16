from __future__ import annotations

from cleo.helpers import argument

from poetry.console.commands.command import Command


class SearchCommand(Command):
    name = "search"
    description = "Searches for packages on remote repositories."

    arguments = [argument("tokens", "The tokens to search for.", multiple=True)]

    def handle(self) -> int:
        from poetry.repositories.pypi_repository import PyPiRepository

        results = PyPiRepository().search(self.argument("tokens"))

        for result in results:
            self.line("")
            name = f"<info>{result.name}</>"

            name += f" (<comment>{result.version}</>)"

            self.line(name)

            if result.description:
                self.line(f" {result.description}")

        return 0
