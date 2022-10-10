from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import Mapping
from typing import Union

from tomlkit import inline_table

from poetry.utils.dependency_specification import parse_dependency_specification


if TYPE_CHECKING:
    from tomlkit.items import InlineTable

    from poetry.console.commands.command import Command
    from poetry.repositories import Pool
    from poetry.utils.env import Env


Requirements = Dict[str, Union[str, Mapping[str, Any]]]


def parse_requirements(
    requirements: list[str], command: Command, env: Env | None
) -> list[dict[str, Any]]:
    from poetry.core.pyproject.exceptions import PyProjectException

    try:
        cwd = command.poetry.file.parent
    except (PyProjectException, RuntimeError):
        cwd = Path.cwd()

    return [
        parse_dependency_specification(
            requirement=requirement,
            env=env,
            cwd=cwd,
        )
        for requirement in requirements
    ]


def format_requirements(requirements: list[dict[str, str]]) -> Requirements:
    requires: Requirements = {}
    for requirement in requirements:
        name = requirement.pop("name")
        constraint: str | InlineTable
        if "version" in requirement and len(requirement) == 1:
            constraint = requirement["version"]
        else:
            constraint = inline_table()
            constraint.trivia.trail = "\n"
            constraint.update(requirement)

        requires[name] = constraint

    return requires


def find_best_version_for_package(
    pool: Pool,
    name: str,
    required_version: str | None = None,
    allow_prereleases: bool = False,
    source: str | None = None,
) -> tuple[str, str]:
    from poetry.version.version_selector import VersionSelector

    selector = VersionSelector(pool)
    package = selector.find_best_candidate(
        name, required_version, allow_prereleases=allow_prereleases, source=source
    )

    if not package:
        # TODO: find similar
        raise ValueError(f"Could not find a matching version of package {name}")

    return package.pretty_name, selector.find_recommended_require_version(package)


def determine_requirements_from_list(
    command: Command,
    pool: Pool,
    requires: list[str],
    allow_prereleases: bool = False,
    source: str | None = None,
) -> list[dict[str, Any]]:
    result = []
    for requirement in parse_requirements(requires, command, None):
        if "git" in requirement or "url" in requirement or "path" in requirement:
            result.append(requirement)
            continue
        elif "version" not in requirement:
            # determine the best version automatically
            name, version = find_best_version_for_package(
                pool,
                requirement["name"],
                allow_prereleases=allow_prereleases,
                source=source,
            )
            requirement["version"] = version
            requirement["name"] = name

            command.line(f"Using version <b>{version}</b> for <c1>{name}</c1>")
        else:
            # check that the specified version/constraint exists
            # before we proceed
            name, _ = find_best_version_for_package(
                pool,
                requirement["name"],
                requirement["version"],
                allow_prereleases=allow_prereleases,
                source=source,
            )

            requirement["name"] = name

        result.append(requirement)

    return result
