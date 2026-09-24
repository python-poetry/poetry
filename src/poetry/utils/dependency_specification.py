from __future__ import annotations

import contextlib
import os
import re
import urllib.parse

from pathlib import Path
from typing import TYPE_CHECKING
from typing import TypeVar
from typing import cast

from poetry.core.packages.dependency import Dependency
from tomlkit.items import InlineTable

from poetry.packages.direct_origin import DirectOrigin


if TYPE_CHECKING:
    from poetry.core.packages.vcs_dependency import VCSDependency

    from poetry.utils.cache import ArtifactCache
    from poetry.utils.env import Env


DependencySpec = dict[str, str | bool | dict[str, str | bool] | list[str]]
BaseSpec = TypeVar("BaseSpec", DependencySpec, InlineTable)

GIT_URL_SCHEMES = {"git+http", "git+https", "git+ssh"}
PACKAGE_ARCHIVE_EXTENSIONS = (".whl", ".tar.gz", ".tar.bz2", ".tar.xz", ".zip")


def dependency_to_specification(
    dependency: Dependency, specification: BaseSpec
) -> BaseSpec:
    if dependency.is_vcs():
        dependency = cast("VCSDependency", dependency)
        assert dependency.source_url is not None
        specification[dependency.vcs] = dependency.source_url
        if dependency.reference:
            specification["rev"] = dependency.reference
    elif dependency.is_file() or dependency.is_directory():
        assert dependency.source_url is not None
        specification["path"] = dependency.source_url
    elif dependency.is_url():
        assert dependency.source_url is not None
        specification["url"] = dependency.source_url
    elif dependency.pretty_constraint != "*" and not dependency.constraint.is_empty():
        specification["version"] = dependency.pretty_constraint

    if not dependency.marker.is_any():
        specification["markers"] = str(dependency.marker)

    if dependency.extras:
        specification["extras"] = sorted(dependency.extras)

    return specification


class RequirementsParser:
    def __init__(
        self,
        *,
        artifact_cache: ArtifactCache,
        env: Env | None = None,
        cwd: Path | None = None,
    ) -> None:
        self._direct_origin = DirectOrigin(artifact_cache)
        self._env = env
        self._cwd = cwd or Path.cwd()

    def parse(self, requirement: str) -> DependencySpec:
        requirement = requirement.strip()
        is_explicit_path = os.path.sep in requirement or "/" in requirement
        is_archive_file = requirement.lower().endswith(PACKAGE_ARCHIVE_EXTENSIONS)
        is_path_like = is_explicit_path or is_archive_file

        if not is_explicit_path and is_archive_file:
            specification = self._parse_path(requirement)
            if specification is not None:
                return specification

        specification = self._parse_pep508(requirement)

        if specification is not None:
            return specification

        extras = []
        extras_m = re.search(r"\[([\w\d,-_ ]+)\]$", requirement)
        if extras_m:
            extras = [e.strip() for e in extras_m.group(1).split(",")]
            requirement, _ = requirement.split("[")

        specification = self._parse_url(requirement)
        if specification is None and is_path_like:
            specification = self._parse_path(requirement)
        specification = specification or self._parse_simple(requirement)

        if specification:
            if extras:
                specification.setdefault("extras", extras)
            return specification

        raise ValueError(f"Invalid dependency specification: {requirement}")

    def _parse_pep508(self, requirement: str) -> DependencySpec | None:
        if " ; " not in requirement and re.search(r"@[\^~!=<>\d]", requirement):
            # this is of the form package@<semver>, do not attempt to parse it
            return None

        with contextlib.suppress(ValueError):
            dependency = Dependency.create_from_pep_508(requirement)
            specification: DependencySpec = {}
            specification = dependency_to_specification(dependency, specification)

            if specification:
                specification["name"] = dependency.name
                return specification

        return None

    def _parse_git_url(self, requirement: str) -> DependencySpec | None:
        from poetry.core.vcs.git import Git
        from poetry.core.vcs.git import ParsedUrl

        parsed = ParsedUrl.parse(requirement)
        url = Git.normalize_url(requirement)

        pair = {"name": parsed.name, "git": url.url}

        if parsed.rev:
            pair["rev"] = url.revision

        if parsed.subdirectory:
            pair["subdirectory"] = parsed.subdirectory

        source_root = self._env.path.joinpath("src") if self._env else None
        package = self._direct_origin.get_package_from_vcs(
            "git",
            url=url.url,
            rev=pair.get("rev"),
            subdirectory=parsed.subdirectory,
            source_root=source_root,
        )
        pair["name"] = package.name
        return pair

    def _parse_url(self, requirement: str) -> DependencySpec | None:
        url_parsed = urllib.parse.urlparse(requirement)
        if not (url_parsed.scheme and url_parsed.netloc):
            return None

        if url_parsed.scheme in GIT_URL_SCHEMES:
            return self._parse_git_url(requirement)

        if url_parsed.scheme in ["http", "https"]:
            package = self._direct_origin.get_package_from_url(requirement)
            assert package.source_url is not None
            return {"name": package.name, "url": package.source_url}

        return None

    def _parse_path(self, requirement: str) -> DependencySpec | None:
        path = Path(requirement).expanduser()
        relative_path = self._cwd.joinpath(requirement)
        is_explicit_path = os.path.sep in requirement or "/" in requirement
        is_relative_path = relative_path.exists()
        is_absolute_path = path.is_absolute() and path.exists()

        if (
            is_relative_path and (is_explicit_path or relative_path.is_file())
        ) or is_absolute_path:
            is_absolute = path.is_absolute()

            if not path.is_absolute():
                path = relative_path

            if path.is_file():
                package = self._direct_origin.get_package_from_file(path.resolve())
            else:
                package = self._direct_origin.get_package_from_directory(path.resolve())

            return {
                "name": package.name,
                "path": (
                    path.relative_to(self._cwd).as_posix()
                    if not is_absolute
                    else path.as_posix()
                ),
            }

        return None

    def _parse_simple(
        self,
        requirement: str,
    ) -> DependencySpec | None:
        extras: list[str] = []
        pair = re.sub(
            "^([^@=: ]+)(?:@|==|(?<![<>~!])=|:| )(.*)$", "\\1 \\2", requirement
        )
        pair = pair.strip()

        require: DependencySpec = {}

        if " " in pair:
            name, version = pair.split(" ", 1)
            extras_m = re.search(r"\[([\w\d,-_]+)\]$", name)
            if extras_m:
                extras = [e.strip() for e in extras_m.group(1).split(",")]
                name, _ = name.split("[")

            require["name"] = name
            if version != "latest":
                require["version"] = version
        else:
            m = re.match(
                r"^([^><=!: ]+)((?:>=|<=|>|<|!=|~=|~|\^).*)$", requirement.strip()
            )
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
