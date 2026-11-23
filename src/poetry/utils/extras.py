from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Collection
    from collections.abc import Iterable
    from collections.abc import Mapping

    from packaging.utils import NormalizedName
    from poetry.core.packages.dependency import Dependency
    from poetry.core.packages.package import Package


def expand_package_extras(
    package: Package, extras: Collection[NormalizedName]
) -> dict[NormalizedName, list[Dependency]]:
    """
    Return dependencies grouped by extra.
    """
    active: dict[NormalizedName, list[Dependency]] = {}
    stack = sorted(extras)
    while stack:
        extra = stack.pop()
        if extra in active:
            continue
        active[extra] = []
        for dependency in package.extras.get(extra, ()):
            if dependency.name == package.name:
                stack.extend(sorted(dependency.extras))
            else:
                active[extra].append(dependency)
    return active


def get_extra_package_names(
    packages: Iterable[Package],
    extras: Mapping[NormalizedName, Iterable[NormalizedName]],
    extra_names: Collection[NormalizedName],
) -> set[NormalizedName]:
    """
    Returns all package names required by the given extras.

    :param packages: A collection of packages, such as from Repository.packages
    :param extras: A mapping of `extras` names to lists of package names, as defined
        in the `extras` section of `poetry.lock`.
    :param extra_names: A list of strings specifying names of extra groups to resolve.
    """
    if not extra_names:
        return set()

    # lookup for packages by name, faster than looping over packages repeatedly
    packages_by_name = {package.name: package for package in packages}

    # Depth-first search, with our entry points being the packages directly required by
    # extras.
    seen_package_names = set()
    stack = [
        extra_package_name
        for extra_name in extra_names
        for extra_package_name in extras.get(extra_name, ())
    ]

    while stack:
        package_name = stack.pop()

        # We expect to find all packages, but can just carry on if we don't.
        package = packages_by_name.get(package_name)
        if package is None or package.name in seen_package_names:
            continue

        seen_package_names.add(package.name)

        stack += [dependency.name for dependency in package.requires]

    return seen_package_names
