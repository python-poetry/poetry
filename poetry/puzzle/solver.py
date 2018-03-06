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

    def __init__(self, package, pool, locked, io):
        self._package = package
        self._pool = pool
        self._locked = locked
        self._io = io

    def solve(self, requested, fixed=None) -> List[Operation]:
        resolver = Resolver(Provider(self._package, self._pool), UI(self._io))

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
            tags = self._get_tags_for_vertex(vertex, requested)
            if 'main' in tags['category']:
                vertex.payload.category = 'main'
            else:
                vertex.payload.category = 'dev'

            if not tags['optional']:
                vertex.payload.optional = False
            else:
                vertex.payload.optional = True
                vertex.payload.requirements = tags['requirements']

        operations = []
        for package in packages:
            installed = False
            for pkg in self._locked.packages:
                if package.name == pkg.name:
                    installed = True
                    # Checking version
                    if package.version != pkg.version:
                        operations.append(Update(pkg, package))

                    break

            if not installed:
                operations.append(Install(package))

        # Checking for removals
        for pkg in self._locked.packages:
            remove = True
            for package in packages:
                if pkg.name == package.name:
                    remove = False
                    break

            if remove:
                operations.append(Uninstall(pkg))

        return list(reversed(operations))

    def _get_tags_for_vertex(self, vertex, requested):
        tags = {
            'category': [],
            'optional': True,
            'requirements': {}
        }

        if not vertex.incoming_edges:
            # Original dependency
            for req in requested:
                if req.name == vertex.name:
                    tags['category'].append(req.category)
                    if not req.is_optional():
                        tags['optional'] = False

                    if req.is_optional():
                        # Checking installation requirements
                        if req.python_versions != '*':
                            tags['requirements']['python'] = str(req.python_constraint)

                        if req.platform != '*':
                            tags['requirements']['platform'] = str(req.platform_constraint)
        else:
            for edge in vertex.incoming_edges:
                sub_tags = self._get_tags_for_vertex(edge.origin, requested)

                tags['category'] += sub_tags['category']
                tags['optional'] = tags['optional'] and sub_tags['optional']
                tags['requirements'].update(sub_tags['requirements'])

        return tags
