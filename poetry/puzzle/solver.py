import time

from typing import Any
from typing import Dict
from typing import List

from poetry.mixology import resolve_version
from poetry.mixology.failure import SolveFailure
from poetry.packages import DependencyPackage
from poetry.packages import Package
from poetry.semver import parse_constraint
from poetry.version.markers import AnyMarker

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
        self._branches = []

    def solve(self, use_latest=None):  # type: (...) -> List[Operation]
        with self._provider.progress():
            start = time.time()
            packages, depths = self._solve(use_latest=use_latest)
            end = time.time()

            if len(self._branches) > 1:
                self._provider.debug(
                    "Complete version solving took {:.3f} seconds for {} branches".format(
                        end - start, len(self._branches[1:])
                    )
                )
                self._provider.debug(
                    "Resolved for branches: {}".format(
                        ", ".join("({})".format(b) for b in self._branches[1:])
                    )
                )

        operations = []
        for package in packages:
            installed = False
            for pkg in self._installed.packages:
                if package.name == pkg.name:
                    installed = True

                    if pkg.source_type == "git" and package.source_type == "git":
                        from poetry.vcs.git import Git

                        # Trying to find the currently installed version
                        pkg_source_url = Git.normalize_url(pkg.source_url)
                        package_source_url = Git.normalize_url(package.source_url)
                        for locked in self._locked.packages:
                            if locked.name != pkg.name or locked.source_type != "git":
                                continue

                            locked_source_url = Git.normalize_url(locked.source_url)
                            if (
                                locked.name == pkg.name
                                and locked.source_type == pkg.source_type
                                and locked_source_url == pkg_source_url
                                and locked.source_reference == pkg.source_reference
                            ):
                                pkg = Package(pkg.name, locked.version)
                                pkg.source_type = "git"
                                pkg.source_url = locked.source_url
                                pkg.source_reference = locked.source_reference
                                break

                        if pkg_source_url != package_source_url or (
                            pkg.source_reference != package.source_reference
                            and not pkg.source_reference.startswith(
                                package.source_reference
                            )
                        ):
                            operations.append(Update(pkg, package))
                        else:
                            operations.append(
                                Install(package).skip("Already installed")
                            )
                    elif package.version != pkg.version:
                        # Checking version
                        operations.append(Update(pkg, package))
                    elif pkg.source_type and package.source_type != pkg.source_type:
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
                o.package.version,
            ),
        )

    def solve_in_compatibility_mode(self, constraints, use_latest=None):
        locked = {}
        for package in self._locked.packages:
            locked[package.name] = DependencyPackage(package.to_dependency(), package)

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
                    else:
                        idx = packages.index(package)
                        pkg = packages[idx]
                        depths[idx] = max(depths[idx], _depths[index])
                        pkg.marker = pkg.marker.union(package.marker)

                        for dep in package.requires:
                            if dep not in pkg.requires:
                                pkg.requires.append(dep)

        return packages, depths

    def _solve(self, use_latest=None):
        self._branches.append(self._package.python_versions)

        locked = {}
        for package in self._locked.packages:
            locked[package.name] = DependencyPackage(package.to_dependency(), package)

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
        final_packages = []
        for package in packages:
            category, optional, marker, depth = self._get_tags_for_package(
                package, graph
            )

            if marker is None:
                marker = AnyMarker()
            if marker.is_empty():
                continue

            package.category = category
            package.optional = optional
            package.marker = marker

            depths.append(depth)
            final_packages.append(package)

        return final_packages, depths

    def _build_graph(
        self, package, packages, previous=None, previous_dep=None, dep=None
    ):  # type: (...) -> Dict[str, Any]
        if not previous:
            category = "dev"
            optional = True
            marker = package.marker
        else:
            category = dep.category
            optional = dep.is_optional() and not dep.is_activated()
            intersection = (
                previous["marker"]
                .without_extras()
                .intersect(previous_dep.transitive_marker.without_extras())
            )
            intersection = intersection.intersect(package.marker.without_extras())

            marker = intersection

        childrens = []  # type: List[Dict[str, Any]]
        graph = {
            "name": package.name,
            "category": category,
            "optional": optional,
            "marker": marker,
            "children": childrens,
        }

        if previous_dep and previous_dep is not dep and previous_dep.name == dep.name:
            return graph

        for dependency in package.all_requires:
            is_activated = True
            if dependency.is_optional():
                if not package.is_root() and (
                    not previous_dep or not previous_dep.extras
                ):
                    continue

                is_activated = False
                for group, extra_deps in package.extras.items():
                    if dep:
                        extras = previous_dep.extras
                    elif package.is_root():
                        extras = package.extras
                    else:
                        extras = []

                    if group in extras and dependency.name in (
                        d.name for d in package.extras[group]
                    ):
                        is_activated = True
                        break

            if previous and previous["name"] == dependency.name:
                # We have a circular dependency.
                # Since the dependencies are resolved we can
                # simply skip it because we already have it
                continue

            for pkg in packages:
                if pkg.name == dependency.name and dependency.constraint.allows(
                    pkg.version
                ):
                    # If there is already a child with this name
                    # we merge the requirements
                    existing = None
                    for child in childrens:
                        if (
                            child["name"] == pkg.name
                            and child["category"] == dependency.category
                        ):
                            existing = child
                            continue

                    child_graph = self._build_graph(
                        pkg, packages, graph, dependency, dep or dependency
                    )

                    if not is_activated:
                        child_graph["optional"] = True

                    if existing:
                        existing["marker"] = existing["marker"].union(
                            child_graph["marker"]
                        )
                        continue

                    childrens.append(child_graph)

        return graph

    def _get_tags_for_package(self, package, graph, depth=0):
        categories = ["dev"]
        optionals = [True]
        markers = []
        _depths = [0]

        children = graph["children"]
        for child in children:
            if child["name"] == package.name:
                category = child["category"]
                optional = child["optional"]
                marker = child["marker"]
                _depths.append(depth)
            else:
                (category, optional, marker, _depth) = self._get_tags_for_package(
                    package, child, depth=depth + 1
                )

                _depths.append(_depth)

            categories.append(category)
            optionals.append(optional)
            if marker is not None:
                markers.append(marker)

        if "main" in categories:
            category = "main"
        else:
            category = "dev"

        optional = all(optionals)

        depth = max(*(_depths + [0]))

        if not markers:
            marker = None
        else:
            marker = markers[0]
            for m in markers[1:]:
                marker = marker.union(m)

        return category, optional, marker, depth
