from __future__ import annotations


class SolverProblemError(Exception):
    def __init__(self, error: Exception) -> None:
        self._error = error

        super().__init__(str(error))

    @property
    def error(self) -> Exception:
        return self._error


class OverrideNeeded(Exception):
    def __init__(self, *overrides: dict) -> None:
        self._overrides = overrides

    @property
    def overrides(self) -> tuple[dict, ...]:
        return self._overrides
