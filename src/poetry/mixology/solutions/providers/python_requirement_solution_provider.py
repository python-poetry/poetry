from __future__ import annotations

import re

from typing import TYPE_CHECKING

from crashtest.contracts.has_solutions_for_exception import HasSolutionsForException


if TYPE_CHECKING:
    from crashtest.contracts.solution import Solution


class PythonRequirementSolutionProvider(HasSolutionsForException):
    def can_solve(self, exception: Exception) -> bool:
        from poetry.puzzle.exceptions import SolverProblemError

        if not isinstance(exception, SolverProblemError):
            return False

        m = re.match(
            "^The current project's Python requirement (.+) is not compatible "
            "with some of the required packages Python requirement",
            str(exception),
        )

        return bool(m)

    def get_solutions(self, exception: Exception) -> list[Solution]:
        from poetry.mixology.solutions.solutions.python_requirement_solution import (
            PythonRequirementSolution,
        )

        return [PythonRequirementSolution(exception)]
