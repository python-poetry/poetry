from __future__ import annotations

import os
import re
import urllib.parse

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Dict
from typing import List
from typing import Union

from poetry.puzzle.provider import Provider


if TYPE_CHECKING:
    from poetry.utils.env import Env


DependencySpec = Dict[str, Union[str, Dict[str, Union[str, bool]], List[str]]]


def _parse_dependency_specification_git_url(
    requirement: str, env: Env | None = None
) -> DependencySpec | None:
    from poetry.core.vcs.git import Git
    from poetry.core.vcs.git import ParsedUrl

    parsed = ParsedUrl.parse(requirement)
    url = Git.normalize_url(requirement)

    pair = {"name": parsed.name, "git": url.url}
    if parsed.rev:
        pair["rev"] = url.revision

    source_root = env.path.joinpath("src") if env else None
    package = Provider.get_package_from_vcs(
        "git", url=url.url, rev=pair.get("rev"), source_root=source_root
    )
    pair["name"] = package.name
    return pair


def _parse_dependency_specification_url(
    requirement: str, env: Env | None = None
) -> DependencySpec | None:
    url_parsed = urllib.parse.urlparse(requirement)
    if not (url_parsed.scheme and url_parsed.netloc):
        return None

    if url_parsed.scheme in ["git+https", "git+ssh"]:
        return _parse_dependency_specification_git_url(requirement, env)

    if url_parsed.scheme in ["http", "https"]:
        package = Provider.get_package_from_url(requirement)
        return {"name": package.name, "url": package.source_url}

    return None


def _parse_dependency_specification_path(
    requirement: str, cwd: Path
) -> DependencySpec | None:
    if (os.path.sep in requirement or "/" in requirement) and (
        cwd.joinpath(requirement).exists()
        or Path(requirement).expanduser().exists()
        and Path(requirement).expanduser().is_absolute()
    ):
        path = Path(requirement).expanduser()
        is_absolute = path.is_absolute()

        if not path.is_absolute():
            path = cwd.joinpath(requirement)

        if path.is_file():
            package = Provider.get_package_from_file(path.resolve())
        else:
            package = Provider.get_package_from_directory(path.resolve())

        return {
            "name": package.name,
            "path": path.relative_to(cwd).as_posix()
            if not is_absolute
            else path.as_posix(),
        }

    return None


def _parse_dependency_specification_simple(
    requirement: str,
) -> DependencySpec | None:
    extras: list[str] = []
    pair = re.sub("^([^@=: ]+)(?:@|==|(?<![<>~!])=|:| )(.*)$", "\\1 \\2", requirement)
    pair = pair.strip()

    require: DependencySpec = {}

    if " " in pair:
        name, version = pair.split(" ", 2)
        extras_m = re.search(r"\[([\w\d,-_]+)\]$", name)
        if extras_m:
            extras = [e.strip() for e in extras_m.group(1).split(",")]
            name, _ = name.split("[")

        require["name"] = name
        if version != "latest":
            require["version"] = version
    else:
        m = re.match(r"^([^><=!: ]+)((?:>=|<=|>|<|!=|~=|~|\^).*)$", requirement.strip())
        if m:
            name, constraint = m.group(1), m.group(2)
            extras_m = re.search(r"\[([\w\d,-_]+)\]$", name)
            if extras_m:
                extras = [e.strip() for e in extras_m.group(1).split(",")]
                name, _ = name.split("[")

            require["name"] = name
            require["version"] = constraint
        else:
            extras_m = re.search(r"\[([\w\d,-_]+)\]$", pair)
            if extras_m:
                extras = [e.strip() for e in extras_m.group(1).split(",")]
                pair, _ = pair.split("[")

            require["name"] = pair

    if extras:
        require["extras"] = extras

    return require


def parse_dependency_specification(
    requirement: str, env: Env | None = None, cwd: Path | None = None
) -> DependencySpec:
    requirement = requirement.strip()
    cwd = cwd or Path.cwd()

    extras = []
    extras_m = re.search(r"\[([\w\d,-_ ]+)\]$", requirement)
    if extras_m:
        extras = [e.strip() for e in extras_m.group(1).split(",")]
        requirement, _ = requirement.split("[")

    specification = (
        _parse_dependency_specification_url(requirement, env=env)
        or _parse_dependency_specification_path(requirement, cwd=cwd)
        or _parse_dependency_specification_simple(requirement)
    )

    if specification:
        if extras and "extras" not in specification:
            specification["extras"] = extras
        return specification

    raise ValueError(f"Invalid dependency specification: {requirement}")
