from typing import TYPE_CHECKING
from typing import Dict
from typing import List

from .version_solver import VersionSolver
from poetry.utils.helpers import with_temp_directory_manager

if TYPE_CHECKING:
    from poetry.core.packages.project_package import ProjectPackage
    from poetry.packages import DependencyPackage
    from poetry.puzzle.provider import Provider

    from .result import SolverResult


def resolve_version(
    root: "ProjectPackage",
    provider: "Provider",
    locked: Dict[str, "DependencyPackage"] = None,
    use_latest: List[str] = None,
) -> "SolverResult":
    with with_temp_directory_manager() as m:
        solver = VersionSolver(root, provider, m, locked=locked, use_latest=use_latest)

    return solver.solve()
