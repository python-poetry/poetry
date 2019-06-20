"""
Strict SEM-VER utilities

The focus of this module is only on sem-ver support and not
full PEP-0440 support, which is not compatible with all the
SEM-VER specs.

https://legacy.python.org/dev/peps/pep-0440/#semantic-versioning
> Semantic versions containing a hyphen (pre-releases - clause 10) or
> a plus sign (builds - clause 11) are not compatible with this PEP
> and are not permitted in the public version field.
"""

from typing import List

import semver


def is_semver(value):  # type: (str) -> bool
    """Check that a string is a single SEM-VER identifier

    :param value: a single SEM-VER identifier
    :return: True if value is a single SEM-VER identifier
    """
    try:
        return bool(semver.VersionInfo.parse(value))
    except (TypeError, ValueError):
        return False


def sorted_semver(values, reverse=False):  # type: (List[str], bool) -> List[str]
    """Sort a list of single SEM-VER constraints (string);
    discards any string that is not a SEM-VER identifier.

    :param values: a list of single SEM-VER identifiers (strings)
    :param reverse: sort descending (reverse=True) or ascending (reverse=False)
    :return: sorted values based on SEM-VER sort criteria
    """
    unsorted = (ver for ver in values if is_semver(ver))
    return sorted(unsorted, key=semver.VersionInfo.parse, reverse=reverse)
