from .version_solver import VersionSolver


def resolve_version(root, provider, locked=None, use_latest=None):
    solver = VersionSolver(root, provider, locked=locked, use_latest=use_latest)

    with provider.progress():
        return solver.solve()
