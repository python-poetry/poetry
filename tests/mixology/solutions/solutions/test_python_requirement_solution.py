from __future__ import annotations

from cleo.io.buffered_io import BufferedIO
from poetry.core.packages.dependency import Dependency

from poetry.mixology.failure import SolveFailure
from poetry.mixology.incompatibility import Incompatibility
from poetry.mixology.incompatibility_cause import PythonCause
from poetry.mixology.term import Term
from poetry.puzzle.exceptions import SolverProblemError


def test_it_provides_the_correct_solution():
    from poetry.mixology.solutions.solutions import PythonRequirementSolution

    incompatibility = Incompatibility(
        [Term(Dependency("foo", "^1.0"), True)], PythonCause("^3.5", ">=3.6")
    )
    exception = SolverProblemError(SolveFailure(incompatibility))
    solution = PythonRequirementSolution(exception)

    title = "Check your dependencies Python requirement."
    description = """\
The Python requirement can be specified via the `python` or `markers` properties

For foo, a possible solution would be to set the `python` property to ">=3.6,<4.0"\
"""
    links = [
        "https://python-poetry.org/docs/dependency-specification/#python-restricted-dependencies",  # noqa: E501
        "https://python-poetry.org/docs/dependency-specification/#using-environment-markers",  # noqa: E501
    ]

    assert title == solution.solution_title
    assert (
        description == BufferedIO().remove_format(solution.solution_description).strip()
    )
    assert links == solution.documentation_links
