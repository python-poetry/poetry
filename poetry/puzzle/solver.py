from typing import List

from poetry.mixology import Resolver
from poetry.mixology.dependency_graph import DependencyGraph
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

    def solve(self, requested, repository, fixed=None) -> List[Operation]:
        resolver = Resolver(Provider(repository), UI(self._io))

        base = None
        if fixed is not None:
            base = DependencyGraph()
            for fixed_req in fixed:
                base.add_vertex(fixed_req.name, fixed_req, True)

        try:
            graph = resolver.resolve(requested, base=base)
        except ResolverError as e:
            raise SolverProblemError(e)

        packages = [v.payload for v in graph.vertices.values()]

        # Setting categories
        for vertex in graph.vertices.values():
            tags = self._get_categories_for_vertex(vertex, requested)
            if 'main' in tags:
                vertex.payload.category = 'main'
            else:
                vertex.payload.category = 'dev'

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

    def _get_categories_for_vertex(self, vertex, requested):
        tags = []
        if not vertex.incoming_edges:
            # Original dependency
            for req in requested:
                if req.name == vertex.name:
                    tags.append(req.category)
        else:
            for edge in vertex.incoming_edges:
                tags += self._get_categories_for_vertex(edge.origin, requested)

        return tags
