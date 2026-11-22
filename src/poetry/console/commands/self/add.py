from __future__ import annotations

import re

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

from poetry.core.constraints.version import Version

from poetry.__version__ import __version__
from poetry.console.commands.add import AddCommand
from poetry.console.commands.self.self_command import SelfCommand
from poetry.utils.dependency_specification import RequirementsParser


if TYPE_CHECKING:
    from cleo.io.inputs.option import Option


class SelfAddCommand(SelfCommand, AddCommand):
    name = "self add"
    description = "Add additional packages to Poetry's runtime environment."
    options: ClassVar[list[Option]] = [
        o
        for o in AddCommand.options
        if o.name in {"editable", "extras", "source", "dry-run", "allow-prereleases"}
    ]
    help = f"""\
The <c1>self add</c1> command installs additional packages to Poetry's runtime \
environment.

This is managed in the <comment>{SelfCommand.get_default_system_pyproject_file()}</> \
file.

{AddCommand.examples}
"""

    @property
    def _hint_update_packages(self) -> str:
        version = Version.parse(__version__)
        flags = ""

        if not version.is_stable():
            flags = " --preview"

        return (
            "\nIf you want to update it to the latest compatible version, you can use"
            f" `poetry self update{flags}`.\nIf you prefer to upgrade it to the latest"
            " available version, you can use `poetry self add package@latest`.\n"
        )

    def _parse_requirements(self, requirements: list[str]) -> list[dict[str, Any]]:
        # Relative paths are relative to the directory Poetry was invoked from,
        # not to the system pyproject.toml in Poetry's config directory.
        # Therefore, they have to be stored as absolute paths.
        parser = RequirementsParser(
            artifact_cache=self.poetry.pool.artifact_cache,
            env=self.env,
            cwd=self._working_directory,
        )

        parsed_requirements = []
        for requirement in requirements:
            parsed = parser.parse(
                re.sub(r"@\s*latest$", "", requirement, flags=re.IGNORECASE)
            )
            path = parsed.get("path")
            if isinstance(path, str) and not Path(path).is_absolute():
                parsed["path"] = (
                    self._working_directory.joinpath(path).resolve().as_posix()
                )
            parsed_requirements.append(parsed)

        return parsed_requirements
