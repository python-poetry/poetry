from poetry.core.packages.dependency import Dependency
from poetry.mixology.failure import SolveFailure
from poetry.mixology.incompatibility import Incompatibility
from poetry.mixology.incompatibility_cause import NoVersionsCause
from poetry.mixology.incompatibility_cause import PythonCause
from poetry.mixology.term import Term
from poetry.puzzle.exceptions import SolverProblemError


def test_it_can_solve_python_incompatibility_solver_errors():
    from poetry.mixology.solutions.providers import PythonRequirementSolutionProvider
    from poetry.mixology.solutions.solutions import PythonRequirementSolution

    incompatibility = Incompatibility(
        [Term(Dependency("foo", "^1.0"), True)], PythonCause("^3.5", ">=3.6")
    )
    exception = SolverProblemError(SolveFailure(incompatibility))
    provider = PythonRequirementSolutionProvider()

    assert provider.can_solve(exception)
    assert isinstance(provider.get_solutions(exception)[0], PythonRequirementSolution)


def test_it_cannot_solve_other_solver_errors():
    from poetry.mixology.solutions.providers import PythonRequirementSolutionProvider

    incompatibility = Incompatibility(
        [Term(Dependency("foo", "^1.0"), True)], NoVersionsCause()
    )
    exception = SolverProblemError(SolveFailure(incompatibility))
    provider = PythonRequirementSolutionProvider()

    assert not provider.can_solve(exception)
