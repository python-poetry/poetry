from __future__ import annotations

from typing import TYPE_CHECKING

from cleo.helpers import argument

from poetry.console.commands.command import Command


if TYPE_CHECKING:
    from cleo.ui.table import Rows


class SourceShowCommand(Command):
    name = "source show"
    description = "Show information about sources configured for the project."

    arguments = [
        argument(
            "source",
            "Source(s) to show information for. Defaults to showing all sources.",
            optional=True,
            multiple=True,
        ),
    ]

    def handle(self) -> int:
        sources = self.poetry.get_sources()
        names = self.argument("source")

        if not sources:
            self.line("No sources configured for this project.")
            return 0

        if names and not any(s.name in names for s in sources):
            self.line_error(
                f"No source found with name(s): {', '.join(names)}",
                style="error",
            )
            return 1

        for source in sources:
            if names and source.name not in names:
                continue

            table = self.table(style="compact")
            rows: Rows = [
                ["<info>name</>", f" : <c1>{source.name}</>"],
                ["<info>url</>", f" : {source.url}"],
                [
                    "<info>priority</>",
                    f" : {source.priority.name.lower()}",
                ],
            ]
            table.add_rows(rows)
            table.render()
            self.line("")

        return 0
