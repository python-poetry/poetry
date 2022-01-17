from copy import deepcopy
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
        option("global", "g", "Set this source to be global"),
    ]

    @staticmethod
    def source_to_table(source: Source) -> "Table":
        source_table: "Table" = table()
        for key, value in source.to_dict().items():
            source_table.add(key, value)
        source_table.add(nl())
        return source_table

    def handle(self) -> Optional[int]:
        from pathlib import Path

        from poetry.core.toml.file import TOMLFile

        from poetry.factory import Factory
        from poetry.locations import CONFIG_DIR
        from poetry.repositories import Pool

        name = self.argument("name")
        url = self.argument("url")
        is_default = self.option("default")
        is_secondary = self.option("secondary")
        is_global = self.option("global")

        if is_default and is_secondary:
            self.line_error(
                "Cannot configure a source as both <c1>default</c1> and"
                " <c1>secondary</c1>."
            )
            return 1

        new_source = Source(
            name=name, url=url, default=is_default, secondary=is_secondary
        )
        existing_global_sources = deepcopy(self.poetry.config.get("sources", {}))
        existing_local_sources = self.poetry.get_sources()
        if is_global:
            existing_sources = [
                Source(name=name, **source)
                for name, source in existing_global_sources.items()
            ]
        else:
            existing_sources = existing_local_sources

        sources_updated = []
        for source in existing_sources:
            if new_source == source:
                self.line(
                    f"Identical source with name <c1>{name}</c1> already exists. "
                    f"Skipping addition."
                )
                return 0

            if name == source.name:
                self.line(f"Source with name <c1>{name}</c1> already exists. Updating.")
                source = new_source
                new_source = None
            elif source.default and new_source.default:
                self.line_error(
                    f"<error>Source with name <c1>{name}</c1> is already set to default. "
                    f"Only one default source can be configured at a time.</error>"
                )
                return 1
            sources_updated.append(source)
        if new_source is not None:
            self.line(f"Adding source with name <c1>{new_source.name}</c1>.")
            sources_updated.append(new_source)

        global_sources = {}
        local_sources = AoT([])
        if is_global:
            for source in sources_updated:
                global_sources[source.name] = source.to_dict()
                global_sources[source.name].pop("name")
        else:
            for source in sources_updated:
                local_sources.append(self.source_to_table(source))

        self.poetry._pool = Pool()
        try:
            Factory.configure_sources(
                self.poetry, local_sources, self.poetry.config, NullIO(), global_sources
            )
            self.poetry.pool.repository(name)
        except ValueError as e:
            self.line_error(
                f"<error>Failed to validate addition of <c1>{name}</c1>: {e}</error>"
            )
            return 1

        if is_global:
            # create system config file if needed.
            config_file = TOMLFile(Path(CONFIG_DIR) / "config.toml")
            if not config_file.exists():
                config_file.path.parent.mkdir(parents=True, exist_ok=True)
                config_file.path.touch(mode=0o0600)

            # only add/update new values
            self.poetry.config.config_source.add_property(f"sources.{name}.url", url)
            self.poetry.config.config_source.add_property(
                f"sources.{name}.default", is_default
            )
            self.poetry.config.config_source.add_property(
                f"sources.{name}.secondary", is_secondary
            )
        else:
            self.poetry.pyproject.poetry_config["source"] = local_sources
            self.poetry.pyproject.save()

        return 0
