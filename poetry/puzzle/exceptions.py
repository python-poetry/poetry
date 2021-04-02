from typing import Dict
from typing import Tuple


class SolverProblemError(Exception):
    def __init__(self, error: Exception) -> None:
        self._error = error

        super().__init__(str(error))

    @property
    def error(self) -> Exception:
        return self._error


class OverrideNeeded(Exception):
    def __init__(self, *overrides: Dict) -> None:
        self._overrides = overrides

    @property
    def overrides(self) -> Tuple[Dict]:
        return self._overrides
