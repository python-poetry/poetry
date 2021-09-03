from typing import TYPE_CHECKING
from typing import Optional
from typing import Union

from poetry.core.packages.project_package import ProjectPackage as _ProjectPackage


if TYPE_CHECKING:
    from poetry.core.semver.version import Version  # noqa


class ProjectPackage(_ProjectPackage):
    def set_version(
        self, version: Union[str, "Version"], pretty_version: Optional[str] = None
    ) -> "ProjectPackage":
        from poetry.core.semver.version import Version  # noqa

        if not isinstance(version, Version):
            self._version = Version.parse(version)
            self._pretty_version = pretty_version or version
        else:
            self._version = version
            self._pretty_version = pretty_version or version.text

        return self
