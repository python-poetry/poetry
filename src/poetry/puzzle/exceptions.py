from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from poetry.core.packages.dependency import Dependency

    from poetry.mixology.failure import SolveFailure
    from poetry.packages import DependencyPackage


class SolverProblemError(Exception):
    def __init__(self, error: SolveFailure) -> None:
        self._error = error

        super().__init__(str(error))

    @property
    def error(self) -> SolveFailure:
        return self._error


class OverrideNeeded(Exception):
    def __init__(
        self, *overrides: dict[DependencyPackage, dict[str, Dependency]]
    ) -> None:
        self._overrides = overrides

    @property
    def overrides(self) -> tuple[dict[DependencyPackage, dict[str, Dependency]], ...]:
        return self._overrides
