from typing import List

from poetry.mixology import Resolver
from poetry.mixology.exceptions import ResolverError

from .exceptions import SolverProblemError
from .operations import Install
from .operations import Uninstall
from .operations import Update
from .operations.operation import Operation

from .provider import Provider
from .ui import UI


class Solver:

    def __init__(self, installed, io):
        self._installed = installed
        self._io = io

    def solve(self, requested, repository) -> List[Operation]:
        resolver = Resolver(Provider(repository), UI(self._io))

        try:
            graph = resolver.resolve(requested)
        except ResolverError as e:
            raise SolverProblemError(e)

        packages = [v.payload for v in graph.vertices.values()]

        operations = []
        for package in packages:
            installed = False
            for pkg in self._installed.packages:
                if package.name == pkg.name:
                    installed = True
                    # Checking version
                    if package.version != pkg.version:
                        operations.append(Update(pkg, package))

                    break

            if not installed:
                operations.append(Install(package))

        # Checking for removals
        for pkg in self._installed.packages:
            remove = True
            for package in packages:
                if pkg.name == package.name:
                    remove = False
                    break

            if remove:
                operations.append(Uninstall(pkg))

        return list(reversed(operations))
