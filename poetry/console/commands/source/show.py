from typing import Optional

from cleo.helpers import argument

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

    def handle(self) -> Optional[int]:
        sources = self.poetry.get_sources()
        names = self.argument("source")

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
                ["<info>name</>", " : <c1>{}</>".format(source.name)],
                ["<info>url</>", " : {}".format(source.url)],
                [
                    "<info>default</>",
                    " : {}".format(bool_string.get(source.default, False)),
                ],
                [
                    "<info>secondary</>",
                    " : {}".format(bool_string.get(source.secondary, False)),
                ],
            ]
            table.add_rows(rows)
            table.render()
            self.line("")

        return 0
