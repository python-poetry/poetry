from typing import Optional

from cleo.helpers import argument
from cleo.helpers import option

from poetry.config.source import Source
from poetry.console.commands.command import Command


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
    options = [
        option("global", "g", "Show global sources"),
        option("all", "a", "Show all sources for project"),
    ]

    def handle(self) -> Optional[int]:
        names = self.argument("source")
        is_global = self.option("global")
        show_all = self.option("all")
        sources = []
        if not is_global or show_all:
            sources.extend(self.poetry.get_sources())

        if is_global or show_all:
            global_sources = self.poetry.config.get("sources", {})
            for name, source in global_sources.items():
                sources.append(Source(name=name, **source))

        if not sources:
            self.line("No sources configured for this project.")
            return 0

        if names and not any(map(lambda s: s.name in names, sources)):
            self.line_error(f"No source found with name(s): {', '.join(names)}")
            return 1

        bool_string = {
            True: "yes",
            False: "no",
        }

        for source in sources:
            if names and source.name not in names:
                continue

            table = self.table(style="compact")
            rows = [
                ["<info>name</>", f" : <c1>{source.name}</>"],
                ["<info>url</>", f" : {source.url}"],
                [
                    "<info>default</>",
                    f" : {bool_string.get(source.default, False)}",
                ],
                [
                    "<info>secondary</>",
                    f" : {bool_string.get(source.secondary, False)}",
                ],
            ]
            table.add_rows(rows)
            table.render()
            self.line("")

        return 0
