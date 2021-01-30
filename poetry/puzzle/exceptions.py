from typing import Dict
from typing import Tuple


class SolverProblemError(Exception):
    def __init__(self, error):  # type: (Exception) -> None
        self._error = error

        super(SolverProblemError, self).__init__(str(error))

    @property
    def error(self):  # type: () -> Exception
        return self._error


class OverrideNeeded(Exception):
    def __init__(self, *overrides):  # type: (*Dict) -> None
        self._overrides = overrides

    @property
    def overrides(self):  # type: () -> Tuple[Dict]
        return self._overrides
