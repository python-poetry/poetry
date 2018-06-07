from .version_solver import VersionSolver


def resolve_version(root, provider, locked=None, use_latest=None):
    solver = VersionSolver(root, provider, locked=locked, use_latest=use_latest)

    return solver.solve()
