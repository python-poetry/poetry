from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Iterator
    from collections.abc import Sequence
    from typing import Mapping

    from poetry.core.packages.package import Package
    from typing_extensions import Literal


def get_extra_package_names(
    packages: Sequence[Package],
    extras: Mapping[str, list[str]],
    extra_names: Sequence[str],
) -> Iterable[str]:
    """
    Returns all package names required by the given extras.

    :param packages: A collection of packages, such as from Repository.packages
    :param extras: A mapping of `extras` names to lists of package names, as defined
        in the `extras` section of `poetry.lock`.
    :param extra_names: A list of strings specifying names of extra groups to resolve.
    """
    from poetry.utils.helpers import canonicalize_name

    if not extra_names:
        return []

    # lookup for packages by name, faster than looping over packages repeatedly
    packages_by_name = {package.name: package for package in packages}

    # get and flatten names of packages we've opted into as extras
    extra_package_names = [
        canonicalize_name(extra_package_name)
        for extra_name in extra_names
        for extra_package_name in extras.get(extra_name, ())
    ]

    # keep record of packages seen during recursion in order to avoid recursion error
    seen_package_names = set()

    def _extra_packages(package_names: Iterable[str]) -> Iterator[str]:
        """Recursively find dependencies for packages names"""
        # for each extra package name
        for package_name in package_names:
            # Find the actual Package object. A missing key indicates an implicit
            # dependency (like setuptools), which should be ignored
            package = packages_by_name.get(canonicalize_name(package_name))
            if package:
                if package.name not in seen_package_names:
                    seen_package_names.add(package.name)
                    yield package.name
                # Recurse for dependencies
                for dependency_package_name in _extra_packages(
                    dependency.name
                    for dependency in package.requires
                    if dependency.name not in seen_package_names
                ):
                    seen_package_names.add(dependency_package_name)
                    yield dependency_package_name

    return _extra_packages(extra_package_names)


def strtobool(val: str) -> Literal[0, 1]:
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return 1
    elif val in ("n", "no", "f", "false", "off", "0"):
        return 0
    else:
        raise ValueError(f"invalid truth value {val!r}")
