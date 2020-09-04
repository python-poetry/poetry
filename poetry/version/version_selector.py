from typing import Union

from poetry.core.packages import Package
from poetry.core.semver import Version


class VersionSelector(object):
    def __init__(self, pool):
        self._pool = pool

    def find_best_candidate(
        self,
        package_name,  # type: str
        target_package_version=None,  # type:  Union[str, None]
        allow_prereleases=False,  # type: bool
        source=None,  # type: str
    ):  # type: (...) -> Union[Package, bool]
        """
        Given a package name and optional version,
        returns the latest Package that matches
        """
        from poetry.factory import Factory

        dependency = Factory.create_dependency(
            package_name,
            {
                "version": target_package_version or "*",
                "allow_prereleases": allow_prereleases,
                "source": source,
            },
        )
        candidates = self._pool.find_packages(dependency)
        only_prereleases = all([c.version.is_prerelease() for c in candidates])

        if not candidates:
            return False

        package = None
        for candidate in candidates:
            if (
                candidate.is_prerelease()
                and not dependency.allows_prereleases()
                and not only_prereleases
            ):
                continue

            # Select highest version of the two
            if package is None or package.version < candidate.version:
                package = candidate

        if package is None:
            return False
        return package

    def find_recommended_require_version(self, package):
        version = package.version

        return self._transform_version(version.text, package.pretty_version)

    def _transform_version(self, version, pretty_version):
        try:
            parsed = Version.parse(version)
            parts = [parsed.major, parsed.minor, parsed.patch]
        except ValueError:
            return pretty_version

        parts = parts[: parsed.precision]

        # check to see if we have a semver-looking version
        if len(parts) < 3:
            version = pretty_version
        else:
            version = ".".join(str(p) for p in parts)
            if parsed.is_prerelease():
                version += "-{}".format(".".join(str(p) for p in parsed.prerelease))

        return "^{}".format(version)
