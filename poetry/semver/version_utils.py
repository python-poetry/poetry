"""
Version utilities

The focus of this module is any version support, but
PEP-0440 support trumps everything else.

With regard to SEM-VER compatibility, PEP-0440 is partially
but not fully compatible with all the SEM-VER specs; see

https://legacy.python.org/dev/peps/pep-0440/#semantic-versioning
> Semantic versions containing a hyphen (pre-releases - clause 10) or
> a plus sign (builds - clause 11) are not compatible with this PEP
> and are not permitted in the public version field.
"""

from typing import List

from poetry.semver import Version


def is_version(value):  # type: (str) -> bool
    """Check that a string is a release version

    :param value: any string
    :return: True if value is a release version
    """
    try:
        return bool(Version.parse(value))
    except (TypeError, ValueError):
        return False


def sorted_versions(values, reverse=False):  # type: (List[str], bool) -> List[str]
    """Sort a list of release versions (string);
    discards any string that is not a release version.

    :param values: a list of strings
    :param reverse: sort descending (reverse=True) or ascending (reverse=False)
    :return: sorted values based on sort criteria for release versions
    """
    unsorted = (ver for ver in values if is_version(ver))
    return sorted(unsorted, key=Version.parse, reverse=reverse)
