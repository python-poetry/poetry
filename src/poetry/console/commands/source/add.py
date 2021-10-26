from typing import TYPE_CHECKING
from typing import Optional

from cleo.helpers import argument
from cleo.helpers import option
from cleo.io.null_io import NullIO
from tomlkit import nl
from tomlkit import table
from tomlkit.items import AoT

from poetry.config.source import Source
from poetry.console.commands.command import Command


if TYPE_CHECKING:
    from tomlkit.items import Table


class SourceAddCommand(Command):

    name = "source add"
    description = "Add source configuration for project."

    arguments = [
        argument(
            "name",
            "Source repository name.",
        ),
        argument("url", "Source repository url."),
    ]

    options = [
        option(
            "default",
            "d",
            "Set this source as the default (disable PyPI). A "
            "default source will also be the fallback source if "
            "you add other sources.",
        ),
        option("secondary", "s", "Set this source as secondary."),
    ]

    @staticmethod
    def source_to_table(source: Source) -> "Table":
        source_table: "Table" = table()
        for key, value in source.to_dict().items():
            source_table.add(key, value)
        source_table.add(nl())
        return source_table

    def handle(self) -> Optional[int]:
        from poetry.factory import Factory
        from poetry.repositories import Pool

        name = self.argument("name")
        url = self.argument("url")
        is_default = self.option("default")
        is_secondary = self.option("secondary")

        if is_default and is_secondary:
            self.line_error(
                "Cannot configure a source as both <c1>default</c1> and <c1>secondary</c1>."
            )
            return 1

        new_source = Source(
            name=name, url=url, default=is_default, secondary=is_secondary
        )
        existing_sources = self.poetry.get_sources()

        sources = AoT([])

        for source in existing_sources:
            if source == new_source:
                self.line(
                    f"Source with name <c1>{name}</c1> already exits. Skipping addition."
                )
                return 0
            elif source.default and is_default:
                self.line_error(
                    f"<error>Source with name <c1>{source.name}</c1> is already set to default. "
                    f"Only one default source can be configured at a time.</error>"
                )
                return 1

            if source.name == name:
                self.line(f"Source with name <c1>{name}</c1> already exits. Updating.")
                source = new_source
                new_source = None

            sources.append(self.source_to_table(source))

        if new_source is not None:
            self.line(f"Adding source with name <c1>{name}</c1>.")
            sources.append(self.source_to_table(new_source))

        self.poetry.config.merge(
            {"sources": {source["name"]: source for source in sources}}
        )

        # ensure new source is valid. eg: invalid name etc.
        self.poetry._pool = Pool()
        try:
            pool = Factory.create_pool(self.poetry.config, NullIO())
            pool.repository(name)
        except ValueError as e:
            self.line_error(
                f"<error>Failed to validate addition of <c1>{name}</c1>: {e}</error>"
            )
            return 1

        self.poetry.pyproject.poetry_config["source"] = sources
        self.poetry.pyproject.save()

        return 0
