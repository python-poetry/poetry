from __future__ import annotations


class PoetryError(Exception):
    pass


class UninterpretableRequirementError(PoetryError):
    """
    A requirement of a package cannot be interpreted because its marker cannot be
    parsed, either because it relies on a newer version of the dependency specifiers
    specification than we support, or because it is syntactically invalid. Ignoring
    such a requirement would silently drop a dependency that may be required at
    runtime, so the package version it belongs to has to be considered unusable.
    """

    def __init__(self, requirement: str, package: str) -> None:
        self.requirement = requirement
        super().__init__(
            f"Unable to interpret requirement ({requirement}) found in {package}"
            " dependencies. Its marker could not be parsed, so it may rely on a newer"
            " version of the dependency specifiers specification than this version of"
            " Poetry supports."
        )
