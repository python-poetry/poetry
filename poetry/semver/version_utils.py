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
from packaging import version as pep440_version


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


def is_package_version(value):  # type: (str) -> bool
    """Check that a string is a PEP-0440 release version
    (or a legacy version).

    :param value: any string
    :return: True if value is a PEP-0440 or legacy version
    """
    try:

        ver = pep440_version.parse(value)
        if isinstance(ver, pep440_version.Version):
            return True
        elif isinstance(ver, pep440_version.LegacyVersion):
            return True
        else:
            return False
    except (pep440_version.InvalidVersion, TypeError, ValueError):
        return False


def sorted_package_versions(
    values, reverse=False
):  # type: (List[str], bool) -> List[str]
    """Sort a list of PEP-0440 release versions (string);
    discards any string that is not a PEP-0440 or legacy version.

    :param values: a list of strings
    :param reverse: sort descending (reverse=True) or ascending (reverse=False)
    :return: sorted values based on sort criteria for PEP-0440 and legacy versions
    """
    unsorted = (ver for ver in values if is_package_version(ver))
    return sorted(unsorted, key=pep440_version.parse, reverse=reverse)


def is_pep440_version(value):  # type: (str) -> bool
    """Check that a string is a PEP-0440 release version
    (or a legacy version).

    :param value: any string
    :return: True if value is a PEP-0440 version
    """
    try:

        ver = pep440_version.parse(value)
        if isinstance(ver, pep440_version.LegacyVersion):
            return False
        elif isinstance(ver, pep440_version.Version):
            return True
        else:
            return False
    except (pep440_version.InvalidVersion, TypeError, ValueError):
        return False


def sorted_pep440_versions(
    values, reverse=False
):  # type: (List[str], bool) -> List[str]
    """Sort a list of PEP-0440 release versions (string);
    discards any string that is not a PEP-0440 release version
    (or a legacy version).

    :param values: a list of strings
    :param reverse: sort descending (reverse=True) or ascending (reverse=False)
    :return: sorted values based on sort criteria for PEP-0440 release versions
    """
    unsorted = (ver for ver in values if is_pep440_version(ver))
    return sorted(unsorted, key=pep440_version.parse, reverse=reverse)


def is_legacy_version(value):  # type: (str) -> bool
    """Check that a string is a legacy version.

    :param value: any string
    :return: True if value is a legacy version
    """
    try:

        ver = pep440_version.parse(value)
        if isinstance(ver, pep440_version.LegacyVersion):
            return True
        elif isinstance(ver, pep440_version.Version):
            return False
        else:
            return False
    except (pep440_version.InvalidVersion, TypeError, ValueError):
        return False


def sorted_legacy_versions(
    values, reverse=False
):  # type: (List[str], bool) -> List[str]
    """Sort a list of legacy versions (string);
    discards any string that is not a legacy version.

    :param values: a list of strings
    :param reverse: sort descending (reverse=True) or ascending (reverse=False)
    :return: sorted values based on sort criteria for legacy release versions
    """
    unsorted = (ver for ver in values if is_legacy_version(ver))
    return sorted(unsorted, key=pep440_version.parse, reverse=reverse)
