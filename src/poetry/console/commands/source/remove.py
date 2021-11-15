from typing import Optional

from cleo.helpers import argument
from tomlkit import nl
from tomlkit import table
from tomlkit.items import AoT
from tomlkit.items import Table

from poetry.config.source import Source
from poetry.console.commands.command import Command


class SourceRemoveCommand(Command):

    name = "source remove"
    description = "Remove source configured for the project."

    arguments = [
        argument(
            "name",
            "Source repository name.",
        ),
    ]

    @staticmethod
    def source_to_table(source: Source) -> Table:
        source_table: Table = table()
        for key, value in source.to_dict().items():
            source_table.add(key, value)
        source_table.add(nl())
        return source_table

    def handle(self) -> Optional[int]:
        name = self.argument("name")

        sources = AoT([])
        removed = False

        for source in self.poetry.get_sources():
            if source.name == name:
                self.line(f"Removing source with name <c1>{source.name}</c1>.")
                removed = True
                continue
            sources.append(self.source_to_table(source))

        if not removed:
            self.line_error(
                f"<error>Source with name <c1>{name}</c1> was not found.</error>"
            )
            return 1

        self.poetry.pyproject.poetry_config["source"] = sources
        self.poetry.pyproject.save()

        return 0
