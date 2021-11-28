from typing import TYPE_CHECKING
from typing import Dict
from typing import List

from poetry.mixology.version_solver import VersionSolver


if TYPE_CHECKING:
    from poetry.core.packages.project_package import ProjectPackage

    from poetry.mixology.result import SolverResult
    from poetry.packages import DependencyPackage
    from poetry.puzzle.provider import Provider


def resolve_version(
    root: "ProjectPackage",
    provider: "Provider",
    locked: Dict[str, "DependencyPackage"] = None,
    use_latest: List[str] = None,
) -> "SolverResult":
    solver = VersionSolver(root, provider, locked=locked, use_latest=use_latest)

    return solver.solve()
