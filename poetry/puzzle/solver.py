from typing import List

from poetry.mixology import Resolver
from poetry.mixology.dependency_graph import DependencyGraph
from poetry.mixology.exceptions import ResolverError

from poetry.semver.version_parser import VersionParser

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

        # Setting info
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

            # Finding the less restrictive requirements
            requirements = {}
            parser = VersionParser()
            for req_name, reqs in tags['requirements'].items():
                for req in reqs:
                    if req_name == 'python':
                        if 'python' not in requirements:
                            requirements['python'] = req
                            continue

                        previous = parser.parse_constraints(requirements['python'])
                        current = parser.parse_constraints(req)

                        if current.matches(previous):
                            requirements['python'] = req

                    if req_name == 'platform':
                        if 'platform' not in requirements:
                            requirements['platform'] = req
                            continue

            vertex.payload.requirements = requirements

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
            'requirements': {
                'python': [],
                'platform': []
            }
        }

        if not vertex.incoming_edges:
            # Original dependency
            for req in requested:
                if req.name == vertex.name:
                    tags['category'].append(req.category)
                    if not req.is_optional():
                        tags['optional'] = False

                    if req.python_versions != '*':
                        tags['requirements']['python'].append(str(req.python_constraint))

                    if req.platform != '*':
                        tags['requirements']['platform'].append(str(req.platform_constraint))

                    break
        else:
            for edge in vertex.incoming_edges:
                for req in edge.origin.payload.requires:
                    if req.name == vertex.payload.name:
                        if req.python_versions != '*':
                            tags['requirements']['python'].append(req.python_versions)

                        if req.platform != '*':
                            tags['requirements']['platform'].append(req.platform)

                sub_tags = self._get_tags_for_vertex(edge.origin, requested)

                tags['category'] += sub_tags['category']
                tags['optional'] = tags['optional'] and sub_tags['optional']
                requirements = sub_tags['requirements']
                tags['requirements']['python'] += requirements.get('python', [])
                tags['requirements']['platform'] += requirements.get('platform', [])

        return tags
