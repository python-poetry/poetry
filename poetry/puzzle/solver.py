from typing import List

from poetry.mixology import resolve_version
from poetry.mixology.failure import SolveFailure
from poetry.packages.constraints.generic_constraint import GenericConstraint

from poetry.semver import parse_constraint

from .exceptions import CompatibilityError
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
        self._provider = Provider(self._package, self._pool, self._io)

    def solve(self, use_latest=None):  # type: (...) -> List[Operation]
        with self._provider.progress():
            packages, depths = self._solve(use_latest=use_latest)

        requested = self._package.all_requires

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

        return sorted(
            operations,
            key=lambda o: (
                o.job_type == "uninstall",
                # Packages to be uninstalled have no depth so we default to 0
                # since it actually doesn't matter since removals are always on top.
                -depths[packages.index(o.package)] if o.job_type != "uninstall" else 0,
                o.package.name,
            ),
        )

    def solve_in_compatibility_mode(self, constraints, use_latest=None):
        locked = {}
        for package in self._locked.packages:
            locked[package.name] = package

        packages = []
        depths = []
        for constraint in constraints:
            constraint = parse_constraint(constraint)
            intersection = constraint.intersect(self._package.python_constraint)

            self._provider.debug(
                "<comment>Retrying dependency resolution "
                "for Python ({}).</comment>".format(intersection)
            )
            with self._package.with_python_versions(str(intersection)):
                _packages, _depths = self._solve(use_latest=use_latest)
                for index, package in enumerate(_packages):
                    if package not in packages:
                        packages.append(package)
                        depths.append(_depths[index])
                        continue

                    current_package = packages[packages.index(package)]
                    for dep in package.requires:
                        if dep not in current_package.requires:
                            current_package.requires.append(dep)

        return packages, depths

    def _solve(self, use_latest=None):
        locked = {}
        for package in self._locked.packages:
            locked[package.name] = package

        try:
            result = resolve_version(
                self._package, self._provider, locked=locked, use_latest=use_latest
            )

            packages = result.packages
        except CompatibilityError as e:
            return self.solve_in_compatibility_mode(
                e.constraints, use_latest=use_latest
            )
        except SolveFailure as e:
            raise SolverProblemError(e)

        graph = self._build_graph(self._package, packages)

        depths = []
        for package in packages:
            category, optional, python, platform, depth = self._get_tags_for_package(
                package, graph
            )
            depths.append(depth)

            package.category = category
            package.optional = optional

            # If requirements are empty, drop them
            requirements = {}
            if python is not None and python != "*":
                requirements["python"] = python

            if platform is not None and platform != "*":
                requirements["platform"] = platform

            package.requirements = requirements

        return packages, depths

    def _build_graph(
        self, package, packages, previous=None, previous_dep=None, dep=None
    ):
        if not previous:
            category = "dev"
            optional = True
            python_version = "*"
            platform = "*"
        else:
            category = dep.category
            optional = dep.is_optional() and not dep.is_activated()
            python_version = str(
                parse_constraint(previous["python_version"]).intersect(
                    previous_dep.python_constraint
                )
            )
            platform = str(
                previous_dep.platform
                if GenericConstraint.parse(previous["platform"]).matches(
                    previous_dep.platform_constraint
                )
                and previous_dep.platform != "*"
                else previous["platform"]
            )

        graph = {
            "name": package.name,
            "category": category,
            "optional": optional,
            "python_version": python_version,
            "platform": platform,
            "children": [],
        }

        if previous_dep and previous_dep is not dep and previous_dep.name == dep.name:
            return graph

        for dependency in package.all_requires:
            if dependency.is_optional():
                if not package.is_root() and (
                    not previous_dep or not previous_dep.extras
                ):
                    continue

                is_activated = False
                for group, extras in package.extras.items():
                    if dep:
                        extras = previous_dep.extras
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
                    # If there is already a child with this name
                    # we merge the requirements
                    existing = None
                    for child in graph["children"]:
                        if (
                            child["name"] == pkg.name
                            and child["category"] == dependency.category
                        ):
                            existing = child
                            continue

                    child_graph = self._build_graph(
                        pkg, packages, graph, dependency, dep or dependency
                    )

                    if existing:
                        existing["python_version"] = str(
                            parse_constraint(existing["python_version"]).union(
                                parse_constraint(child_graph["python_version"])
                            )
                        )
                        continue

                    graph["children"].append(child_graph)

        return graph

    def _get_tags_for_package(self, package, graph, depth=0):
        categories = ["dev"]
        optionals = [True]
        python_versions = []
        platforms = []
        _depths = [0]

        children = graph["children"]
        found = False
        for child in children:
            if child["name"] == package.name:
                category = child["category"]
                optional = child["optional"]
                python_version = child["python_version"]
                platform = child["platform"]
                _depths.append(depth)
            else:
                (
                    category,
                    optional,
                    python_version,
                    platform,
                    _depth,
                ) = self._get_tags_for_package(package, child, depth=depth + 1)

                _depths.append(_depth)

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

        depth = max(*(_depths + [0]))

        return category, optional, python_version, platform, depth
