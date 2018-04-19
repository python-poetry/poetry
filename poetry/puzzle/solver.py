from typing import List

from poetry.mixology import Resolver
from poetry.mixology.dependency_graph import DependencyGraph
from poetry.mixology.exceptions import ResolverError
from poetry.packages.constraints.generic_constraint import GenericConstraint

from poetry.semver.version_parser import VersionParser

from .exceptions import SolverProblemError
from .operations import Install
from .operations import Uninstall
from .operations import Update
from .operations.operation import Operation

from .provider import Provider
from .ui import UI


class Solver:

    def __init__(self, package, pool, installed, locked, io):
        self._package = package
        self._pool = pool
        self._installed = installed
        self._locked = locked
        self._io = io

    def solve(self, requested, fixed=None):  # type: (...) -> List[Operation]
        resolver = Resolver(
            Provider(self._package, self._pool, self._io),
            UI(self._io)
        )

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
            category, optional, python, platform = self._get_tags_for_vertex(
                vertex, requested
            )

            vertex.payload.category = category
            vertex.payload.optional = optional

            # If requirements are empty, drop them
            requirements = {}
            if python is not None and python != '*':
                requirements['python'] = python

            if platform is not None and platform != '*':
                requirements['platform'] = platform

            vertex.payload.requirements = requirements

        operations = []
        for package in packages:
            installed = False
            for pkg in self._installed.packages:
                if package.name == pkg.name:
                    installed = True
                    # Checking version
                    if package.version != pkg.version:
                        operations.append(Update(pkg, package))
                    else:
                        operations.append(
                            Install(package).skip('Already installed')
                        )

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
                skip = True
                for installed in self._installed.packages:
                    if installed.name == pkg.name:
                        skip = False
                        break

                op = Uninstall(pkg)
                if skip:
                    op.skip('Not currently installed')

                operations.append(op)

        requested_names = [r.name for r in requested]

        return sorted(
            operations,
            key=lambda o: (
                1 if not o.package.name not in requested_names else 0,
                o.package.name
            )
        )

    def _get_tags_for_vertex(self, vertex, requested):
        category = 'dev'
        optional = True
        python_version = None
        platform = None

        if not vertex.incoming_edges:
            # Original dependency
            for req in requested:
                if vertex.payload.name == req.name:
                    category = req.category
                    optional = req.is_optional()

                    python_version = str(req.python_constraint)

                    platform = str(req.platform_constraint)

                    break

            return category, optional, python_version, platform

        parser = VersionParser()
        python_versions = []
        platforms = []
        for edge in vertex.incoming_edges:
            python_version = None
            platform = None
            for req in edge.origin.payload.requires:
                if req.name == vertex.payload.name:
                    python_version = req.python_versions
                    platform = req.platform

                    break

            (top_category,
             top_optional,
             top_python_version,
             top_platform) = self._get_tags_for_vertex(
                edge.origin, requested
            )

            if top_category == 'main':
                category = top_category

            optional = optional and top_optional

            # Take the most restrictive constraints
            if top_python_version is not None:
                if python_version is not None:
                    previous = parser.parse_constraints(python_version)
                    current = parser.parse_constraints(top_python_version)

                    if top_python_version != '*' and previous.matches(current):
                        python_versions.append(top_python_version)
                    else:
                        python_versions.append(python_version)
                else:
                    python_versions.append(top_python_version)
            elif python_version is not None:
                python_versions.append(python_version)

            if top_platform is not None:
                if platform is not None:
                    previous = GenericConstraint.parse(platform)
                    current = GenericConstraint.parse(top_platform)

                    if top_platform != '*' and previous.matches(current):
                        platforms.append(top_platform)
                    else:
                        platforms.append(platform)
                else:
                    platforms.append(top_platform)
            elif platform is not None:
                platforms.append(platform)

        if not python_versions:
            python_version = None
        else:
            # Find the least restrictive constraint
            python_version = python_versions[0]
            previous = parser.parse_constraints(python_version)
            for constraint in python_versions[1:]:
                current = parser.parse_constraints(constraint)

                if python_version == '*':
                    continue
                elif constraint == '*':
                    python_version = constraint
                elif current.matches(previous):
                    python_version = constraint

        if not platforms:
            platform = None
        else:
            platform = platforms[0]
            previous = GenericConstraint.parse(platform)
            for constraint in platforms[1:]:
                current = GenericConstraint.parse(constraint)

                if platform == '*':
                    continue
                elif constraint == '*':
                    platform = constraint
                elif current.matches(previous):
                    platform = constraint

        return category, optional, python_version, platform
