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
            result = resolve_version(
                self._package, provider, locked=locked, use_latest=use_latest
            )
        except SolveFailure as e:
            raise SolverProblemError(e)

        packages = result.packages
        requested = self._package.all_requires

        for package in packages:
            graph = self._build_graph(self._package, packages)
            category, optional, python, platform = self._get_tags_for_package(
                package, graph
            )

            package.category = category
            package.optional = optional

            # If requirements are empty, drop them
            requirements = {}
            if python is not None and python != "*":
                requirements["python"] = python

            if platform is not None and platform != "*":
                requirements["platform"] = platform

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
                        operations.append(Install(package).skip("Already installed"))

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
                    op.skip("Not currently installed")

                operations.append(op)

        requested_names = [r.name for r in self._package.all_requires]

        return sorted(
            operations,
            key=lambda o: (
                1 if o.package.name in requested_names else 0,
                o.package.name,
            ),
        )

    def _build_graph(self, package, packages, previous=None, dep=None):
        if not previous:
            category = "dev"
            optional = True
            python_version = None
            platform = None
        else:
            category = dep.category
            optional = dep.is_optional() and not dep.is_activated()
            python_version = (
                dep.python_versions
                if previous.python_constraint.allows_all(dep.python_constraint)
                else previous.python_versions
            )
            platform = (
                dep.platform
                if previous.platform_constraint.matches(dep.platform_constraint)
                and dep.platform != "*"
                else previous.platform
            )

        graph = {
            "name": package.name,
            "category": category,
            "optional": optional,
            "python_version": python_version,
            "platform": platform,
            "children": [],
        }

        if previous and previous is not dep and previous.name == dep.name:
            return graph

        for dependency in package.all_requires:
            if dependency.is_optional():
                if not package.is_root() and (not dep or not dep.extras):
                    continue

                is_activated = False
                for group, extras in package.extras.items():
                    if dep:
                        extras = dep.extras
                    elif package.is_root():
                        extras = package.extras
                    else:
                        extras = []

                    if group in extras:
                        is_activated = True
                        break

                if not is_activated:
                    continue

            for pkg in packages:
                if pkg.name == dependency.name:
                    graph["children"].append(
                        self._build_graph(pkg, packages, dependency, dep or dependency)
                    )

        return graph

    def _get_tags_for_package(self, package, graph):
        categories = ["dev"]
        optionals = [True]
        python_versions = []
        platforms = []

        children = graph["children"]
        for child in children:
            if child["name"] == package.name:
                category = child["category"]
                optional = child["optional"]
                python_version = child["python_version"]
                platform = child["platform"]
            else:
                (
                    category,
                    optional,
                    python_version,
                    platform,
                ) = self._get_tags_for_package(package, child)

            categories.append(category)
            optionals.append(optional)
            if python_version is not None:
                python_versions.append(python_version)

            if platform is not None:
                platforms.append(platform)

        if "main" in categories:
            category = "main"
        else:
            category = "dev"

        optional = all(optionals)

        if not python_versions:
            python_version = None
        else:
            # Find the least restrictive constraint
            python_version = python_versions[0]
            for constraint in python_versions[1:]:
                previous = parse_constraint(python_version)
                current = parse_constraint(constraint)

                if python_version == "*":
                    continue
                elif constraint == "*":
                    python_version = constraint
                elif current.allows_all(previous):
                    python_version = constraint

        if not platforms:
            platform = None
        else:
            platform = platforms[0]
            for constraint in platforms[1:]:
                previous = GenericConstraint.parse(platform)
                current = GenericConstraint.parse(constraint)

                if platform == "*":
                    continue
                elif constraint == "*":
                    platform = constraint
                elif current.matches(previous):
                    platform = constraint

        return category, optional, python_version, platform
