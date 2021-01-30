from typing import TYPE_CHECKING
from typing import Dict
from typing import List

from .version_solver import VersionSolver


if TYPE_CHECKING:
    from poetry.core.packages import DependencyPackage  # noqa
    from poetry.core.packages import ProjectPackage  # noqa
    from poetry.puzzle.provider import Provider  # noqa

    from .result import SolverResult  # noqa


def resolve_version(
    root, provider, locked=None, use_latest=None
):  # type: ("ProjectPackage", "Provider", Dict[str, "DependencyPackage"],List[str])  -> "SolverResult"
    solver = VersionSolver(root, provider, locked=locked, use_latest=use_latest)

    return solver.solve()
