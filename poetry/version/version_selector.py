from typing import Union

from poetry.packages import Dependency
from poetry.packages import Package
from poetry.semver import parse_constraint
from poetry.semver import Version


class VersionSelector(object):
    def __init__(self, pool):
        self._pool = pool

    def find_best_candidate(
        self,
        package_name,  # type: str
        target_package_version=None,  # type:  Union[str, None]
        allow_prereleases=False,  # type: bool
    ):  # type: (...) -> Union[Package, bool]
        """
        Given a package name and optional version,
        returns the latest Package that matches
        """
        if target_package_version:
            constraint = parse_constraint(target_package_version)
        else:
            constraint = parse_constraint("*")

        candidates = self._pool.find_packages(
            package_name, constraint, allow_prereleases=allow_prereleases
        )

        if not candidates:
            return False

        dependency = Dependency(package_name, constraint)

        # Select highest version if we have many
        package = candidates[0]
        for candidate in candidates:
            if candidate.is_prerelease() and not dependency.allows_prereleases():
                continue

            # Select highest version of the two
            if package.version < candidate.version:
                package = candidate

        return package

    def find_recommended_require_version(self, package):
        version = package.version

        return self._transform_version(version.text, package.pretty_version)

    def _transform_version(self, version, pretty_version):
        # attempt to transform 2.1.1 to 2.1
        # this allows you to upgrade through minor versions
        try:
            parsed = Version.parse(version)
            parts = [parsed.major, parsed.minor, parsed.patch]
        except ValueError:
            return pretty_version

        # check to see if we have a semver-looking version
        if len(parts) == 3:
            # remove the last parts (the patch version number and any extra)
            if parts[0] != 0:
                del parts[2]

            version = ".".join(str(p) for p in parts)
            if parsed.is_prerelease():
                version += "-{}".format(".".join(str(p) for p in parsed.prerelease))
        else:
            return pretty_version

        return "^{}".format(version)
