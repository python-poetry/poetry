class SolverResult:
    def __init__(self, root, packages, attempted_solutions):
        self._root = root
        self._packages = packages
        self._attempted_solutions = attempted_solutions

    @property
    def packages(self):
        return self._packages

    @property
    def attempted_solutions(self):
        return self._attempted_solutions
