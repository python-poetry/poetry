from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

from cleo.helpers import argument
from tomlrt import AoT

from poetry.console.commands.command import Command


if TYPE_CHECKING:
    from collections.abc import Mapping

    from cleo.io.inputs.argument import Argument


class SourceRemoveCommand(Command):
    name = "source remove"
    description = "Remove source configured for the project."

    arguments: ClassVar[list[Argument]] = [
        argument(
            "name",
            "Source repository name.",
        ),
    ]

    def handle(self) -> int:
        name = self.argument("name")
        lower_name = name.lower()

        if referenced := self._dependencies_referencing(lower_name):
            self.line_error(
                f'<error>Cannot remove source "{name}" because it is still referenced '
                f"by the following dependencies: {', '.join(referenced)}.</error>"
                "\nRemove them first or point them at another source."
            )
            return 1

        sources = AoT([])
        removed = False

        for source in self.poetry.get_sources():
            if source.name.lower() == lower_name:
                self.line(f"Removing source with name <c1>{source.name}</c1>.")
                removed = True
                continue
            sources.append(source.to_toml_table())

        if not removed:
            self.line_error(
                f"<error>Source with name <c1>{name}</c1> was not found.</error>"
            )
            return 1

        self.poetry.pyproject.poetry_config["source"] = sources
        self.poetry.pyproject.save()

        return 0

    def _dependencies_referencing(self, lower_name: str) -> list[str]:
        """Dependencies that would point at a source that no longer exists."""
        poetry_config: Mapping[str, Any] = self.poetry.pyproject.poetry_config
        declarations: list[Mapping[str, Any]] = []
        if "dependencies" in poetry_config:
            declarations.append(poetry_config["dependencies"])
        for group in poetry_config.get("group", {}).values():
            if "dependencies" in group:
                declarations.append(group["dependencies"])

        referenced: set[str] = set()
        for declaration in declarations:
            for dependency_name, constraint in declaration.items():
                constraints = (
                    constraint if isinstance(constraint, list) else [constraint]
                )
                for item in constraints:
                    if (
                        isinstance(item, dict)
                        and str(item.get("source", "")).lower() == lower_name
                    ):
                        referenced.add(dependency_name)

        return sorted(referenced)
