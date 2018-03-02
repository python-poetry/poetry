import re
from typing import Union

from poetry.packages import Package
from poetry.semver.comparison import less_than
from poetry.semver.helpers import normalize_version
from poetry.semver.version_parser import VersionParser


class VersionSelector(object):

    def __init__(self, pool, parser=VersionParser()):
        self._pool = pool
        self._parser = parser

    def find_best_candidate(self,
                            package_name: str,
                            target_package_version: Union[str, None] = None
                            ) -> Union[Package, bool]:
        """
        Given a package name and optional version,
        returns the latest Package that matches
        """
        if target_package_version:
            constraint = self._parser.parse_constraints(target_package_version)
        else:
            constraint = None

        candidates = self._pool.find_packages(package_name, constraint)

        if not candidates:
            return False

        # Select highest version if we have many
        package = candidates[0]
        for candidate in candidates:
            # Select highest version of the two
            if less_than(package.version, candidate.version):
                package = candidate

        return package

    def find_recommended_require_version(self, package):
        version = package.version

        return self._transform_version(version, package.pretty_version)

    def _transform_version(self, version, pretty_version):
        # attempt to transform 2.1.1 to 2.1
        # this allows you to upgrade through minor versions
        try:
            parts = normalize_version(version).split('.')
        except ValueError:
            return pretty_version

        # check to see if we have a semver-looking version
        if len(parts) == 4 and re.match('^0\D?', parts[3]):
            # remove the last parts (the patch version number and any extra)
            if parts[0] == '0':
                del parts[3]
            else:
                del parts[3]
                del parts[2]

            version = '.'.join(parts)
        else:
            return pretty_version

        return f'^{version}'
