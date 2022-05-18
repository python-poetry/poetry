from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.core.packages.project_package import ProjectPackage as _ProjectPackage


if TYPE_CHECKING:
    from poetry.core.semver.version import Version


class ProjectPackage(_ProjectPackage):  # type: ignore[misc]
    def set_version(
        self, version: str | Version, pretty_version: str | None = None
    ) -> None:
        from poetry.core.semver.version import Version

        if not isinstance(version, Version):
            self._version = Version.parse(version)
            self._pretty_version = pretty_version or version
        else:
            self._version = version
            self._pretty_version = pretty_version or version.text
