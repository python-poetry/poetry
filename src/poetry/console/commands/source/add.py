from __future__ import annotations

from cleo.helpers import argument
from cleo.helpers import option
from cleo.io.null_io import NullIO
from tomlkit.items import AoT

from poetry.config.source import Source
from poetry.console.commands.command import Command
from poetry.repositories.repository_pool import Priority


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
            (
                "Set this source as the default (disable PyPI). A "
                "default source will also be the fallback source if "
                "you add other sources. (<warning>Deprecated</warning>, use --priority)"
            ),
        ),
        option(
            "secondary",
            "s",
            (
                "Set this source as secondary. (<warning>Deprecated</warning>, use"
                " --priority)"
            ),
        ),
        option(
            "priority",
            "p",
            (
                "Set the priority of this source. One of:"
                f" {', '.join(p.name.lower() for p in Priority)}. Defaults to"
                f" {Priority.PRIMARY.name.lower()}."
            ),
            flag=False,
        ),
    ]

    def handle(self) -> int:
        from poetry.factory import Factory
        from poetry.utils.source import source_to_table

        name: str = self.argument("name")
        url: str = self.argument("url")
        is_default: bool = self.option("default", False)
        is_secondary: bool = self.option("secondary", False)
        priority: Priority | None = self.option("priority", None)

        if is_default and is_secondary:
            self.line_error(
                "<error>Cannot configure a source as both <c1>default</c1> and"
                " <c1>secondary</c1>.</error>"
            )
            return 1

        if is_default or is_secondary:
            if priority is not None:
                self.line_error(
                    "<error>Priority was passed through both --priority and a"
                    " deprecated flag (--default or --secondary). Please only provide"
                    " one of these.</error>"
                )
                return 1
            else:
                self.line_error(
                    "<warning>Warning: Priority was set through a deprecated flag"
                    " (--default or --secondary). Consider using --priority next"
                    " time.</warning>"
                )

        if is_default:
            priority = Priority.DEFAULT
        elif is_secondary:
            priority = Priority.SECONDARY
        elif priority is None:
            priority = Priority.PRIMARY

        new_source = Source(name=name, url=url, priority=priority)
        existing_sources = self.poetry.get_sources()

        sources = AoT([])

        is_new_source = True
        for source in existing_sources:
            if source == new_source:
                self.line(
                    f"Source with name <c1>{name}</c1> already exists. Skipping"
                    " addition."
                )
                return 0
            elif (
                source.priority is Priority.DEFAULT
                and new_source.priority is Priority.DEFAULT
            ):
                self.line_error(
                    f"<error>Source with name <c1>{source.name}</c1> is already set to"
                    " default. Only one default source can be configured at a"
                    " time.</error>"
                )
                return 1

            if source.name == name:
                source = new_source
                is_new_source = False

            sources.append(source_to_table(source))

        if is_new_source:
            self.line(f"Adding source with name <c1>{name}</c1>.")
            sources.append(source_to_table(new_source))
        else:
            self.line(f"Source with name <c1>{name}</c1> already exists. Updating.")

        # ensure new source is valid. eg: invalid name etc.
        try:
            pool = Factory.create_pool(self.poetry.config, sources, NullIO())
            pool.repository(name)
        except ValueError as e:
            self.line_error(
                f"<error>Failed to validate addition of <c1>{name}</c1>: {e}</error>"
            )
            return 1

        self.poetry.pyproject.poetry_config["source"] = sources
        self.poetry.pyproject.save()

        return 0
