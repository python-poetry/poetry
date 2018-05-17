from typing import List

from poetry.mixology import resolve_version
from poetry.mixology.failure import SolveFailure
from poetry.packages.constraints.generic_constraint import GenericConstraint

from poetry.semver import parse_constraint

from .exceptions import SolverProblemError

from .operations import Install
from .operations import Uninstall
from .operations import Update
from .operations.operation import Operation

from .provider import Provider


class Solver:

    def __init__(self, package, pool, installed, locked, io):
        self._package = package
        self._pool = pool
        self._installed = installed
        self._locked = locked
        self._io = io

    def solve(self, use_latest=None):  # type: (...) -> List[Operation]
        provider = Provider(self._package, self._pool, self._io)
        locked = {}
        for package in self._locked.packages:
            locked[package.name] = package

        try:
            result = resolve_version(self._package, provider, locked=locked, use_latest=use_latest)
        except SolveFailure as e:
            raise SolverProblemError(e)

        packages = result.packages
        requested = self._package.all_requires

        for package in packages:
            category, optional, python, platform = self._get_tags_for_package(
                package, packages, requested
            )

            package.category = category
            package.optional = optional

            # If requirements are empty, drop them
            requirements = {}
            if python is not None and python != '*':
                requirements['python'] = python

            if platform is not None and platform != '*':
                requirements['platform'] = platform

            package.requirements = requirements

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

        requested_names = [r.name for r in self._package.all_requires]

        return sorted(
            operations,
            key=lambda o: (
                1 if not o.package.name not in requested_names else 0,
                o.package.name
            )
        )

    def _get_tags_for_package(self, package, packages, requested, original=None):
        category = 'dev'
        optional = True

        root = None
        for dep in requested:
            if dep.name == package.name:
                root = dep

        origins = []
        for pkg in packages:
            for dep in pkg.all_requires:
                if original and original.name == pkg.name:
                    # Circular dependency
                    continue

                if dep.name == package.name:
                    origins.append((pkg, dep))

        if root is not None and not origins:
            # Original dependency
            category = root.category
            optional = root.is_optional()

            python_version = str(root.python_constraint)
            platform = str(root.platform_constraint)

            return category, optional, python_version, platform

        python_versions = []
        platforms = []

        for pkg, dep in origins:
            python_version = dep.python_versions
            platform = dep.platform

            (top_category,
             top_optional,
             top_python_version,
             top_platform) = self._get_tags_for_package(
                pkg, packages, requested, original=package
            )

            if top_category == 'main':
                category = top_category

            optional = optional and top_optional

            # Take the most restrictive constraints
            if top_python_version is not None:
                if python_version is not None:
                    previous = parse_constraint(python_version)
                    current = parse_constraint(top_python_version)

                    if previous.allows_all(current):
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
            previous = parse_constraint(python_version)
            for constraint in python_versions[1:]:
                current = parse_constraint(constraint)

                if python_version == '*':
                    continue
                elif constraint == '*':
                    python_version = constraint
                elif current.allows_all(previous):
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
