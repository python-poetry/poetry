from __future__ import annotations

import re

from typing import TYPE_CHECKING

from crashtest.contracts.has_solutions_for_exception import HasSolutionsForException

from poetry.puzzle.exceptions import SolverProblemError


if TYPE_CHECKING:
    from crashtest.contracts.solution import Solution


class PythonRequirementSolutionProvider(HasSolutionsForException):
    def can_solve(self, exception: Exception) -> bool:
        if not isinstance(exception, SolverProblemError):
            return False

        m = re.match(
            "^The current project's supported Python range (.+) is not compatible "
            "with some of the required packages Python requirement",
            str(exception),
        )

        return bool(m)

    def get_solutions(self, exception: Exception) -> list[Solution]:
        from poetry.mixology.solutions.solutions.python_requirement_solution import (
            PythonRequirementSolution,
        )

        assert isinstance(exception, SolverProblemError)
        return [PythonRequirementSolution(exception)]
