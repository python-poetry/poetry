from __future__ import annotations

from cleo.helpers import argument

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

    def render_source(self, source: Source) -> None:
        bool_string = {
            True: "yes",
            False: "no",
        }

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

    def handle(self) -> int | None:
        sources = self.poetry.get_sources()
        names = self.argument("source")

        if names and "pypi" not in names and not any(s.name in names for s in sources):
            self.line_error(f"No source found with name(s): {', '.join(names)}")
            return 1

        for repositories, secondary in [
            (self.poetry.pool.primary_repositories, False),
            (self.poetry.pool.secondary_repositories, True),
        ]:
            for repository in repositories:
                if names and repository.name not in names:
                    continue

                self.render_source(
                    Source(
                        name=repository.name or "-",
                        url=getattr(repository, "url", "-"),
                        default=repository is self.poetry.pool.default_repository,
                        secondary=secondary,
                    )
                )

        if names or not self.io.is_verbose():
            return 0

        self.write(
            "<c2>Poetry will search <warning>all</> of the above package sources when "
            "searching for packages.</>\n"
        )

        if len(self.poetry.pool.repositories) <= 1:
            return 0

        self.line("")

        first = self.poetry.pool.repositories[0].name or ""
        last = self.poetry.pool.repositories[-1].name or ""

        if first and last:
            self.write(
                "<c2>All other things equal, for a give package that is available from"
                " multiple sources, it will be preferred in the order listed"
                " above.</>\n\n<warning>For example, if a package <c2>foo</> is"
                f" available in both <c1>{first}</> and <c1>{last}</>, Poetry will"
                f" select <c1>{first}</>.\n\nYou can override this, by explicitly"
                " specify the source when adding the package.\n\n    $ <c2>poetry add"
                f" --source {last} foo</>\n\n</>"
            )

            if first.lower() != "pypi":
                self.write(
                    "<warning>Alternatively, you can set <c2>all</> your custom sources"
                    " as <c2>secondary</>.</>\n"
                )

            self.line("")

        return 0
