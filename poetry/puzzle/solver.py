import enum
import time

from collections import defaultdict
from contextlib import contextmanager
from typing import List
from typing import Optional

from clikit.io import ConsoleIO

from poetry.core.packages import Package
from poetry.core.packages.project_package import ProjectPackage
from poetry.installation.operations import Install
from poetry.installation.operations import Uninstall
from poetry.installation.operations import Update
from poetry.installation.operations.operation import Operation
from poetry.mixology import resolve_version
from poetry.mixology.failure import SolveFailure
from poetry.packages import DependencyPackage
from poetry.repositories import Pool
from poetry.repositories import Repository
from poetry.utils.env import Env

from .exceptions import OverrideNeeded
from .exceptions import SolverProblemError
from .provider import Provider


class Solver:
    def __init__(
        self,
        package,  # type: ProjectPackage
        pool,  # type: Pool
        installed,  # type: Repository
        locked,  # type: Repository
        io,  # type: ConsoleIO
        remove_untracked=False,  # type: bool
        provider=None,  # type: Optional[Provider]
    ):
        self._package = package
        self._pool = pool
        self._installed = installed
        self._locked = locked
        self._io = io

        if provider is None:
            provider = Provider(self._package, self._pool, self._io)

        self._provider = provider
        self._overrides = []
        self._remove_untracked = remove_untracked

    @property
    def provider(self):  # type: () -> Provider
        return self._provider

    @contextmanager
    def use_environment(self, env):  # type: (Env) -> None
        with self.provider.use_environment(env):
            yield

    def solve(self, use_latest=None):  # type: (...) -> List[Operation]
        with self._provider.progress():
            start = time.time()
            packages, depths = self._solve(use_latest=use_latest)
            end = time.time()

            if len(self._overrides) > 1:
                self._provider.debug(
                    "Complete version solving took {:.3f} seconds with {} overrides".format(
                        end - start, len(self._overrides)
                    )
                )
                self._provider.debug(
                    "Resolved with overrides: {}".format(
                        ", ".join("({})".format(b) for b in self._overrides)
                    )
                )

        operations = []
        for i, package in enumerate(packages):
            installed = False
            for pkg in self._installed.packages:
                if package.name == pkg.name:
                    installed = True

                    if pkg.source_type == "git" and package.source_type == "git":
                        from poetry.core.vcs.git import Git

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
                                and locked.source_resolved_reference
                                == pkg.source_resolved_reference
                            ):
                                pkg = Package(
                                    pkg.name,
                                    locked.version,
                                    source_type="git",
                                    source_url=locked.source_url,
                                    source_reference=locked.source_reference,
                                    source_resolved_reference=locked.source_resolved_reference,
                                )
                                break

                        if pkg_source_url != package_source_url or (
                            (
                                not pkg.source_resolved_reference
                                or not package.source_resolved_reference
                            )
                            and pkg.source_reference != package.source_reference
                            and not pkg.source_reference.startswith(
                                package.source_reference
                            )
                            or (
                                pkg.source_resolved_reference
                                and package.source_resolved_reference
                                and pkg.source_resolved_reference
                                != package.source_resolved_reference
                                and not pkg.source_resolved_reference.startswith(
                                    package.source_resolved_reference
                                )
                            )
                        ):
                            operations.append(Update(pkg, package, priority=depths[i]))
                        else:
                            operations.append(
                                Install(package).skip("Already installed")
                            )
                    elif package.version != pkg.version:
                        # Checking version
                        operations.append(Update(pkg, package, priority=depths[i]))
                    elif pkg.source_type and package.source_type != pkg.source_type:
                        operations.append(Update(pkg, package, priority=depths[i]))
                    else:
                        operations.append(
                            Install(package, priority=depths[i]).skip(
                                "Already installed"
                            )
                        )

                    break

            if not installed:
                operations.append(Install(package, priority=depths[i]))

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

        if self._remove_untracked:
            locked_names = {locked.name for locked in self._locked.packages}

            for installed in self._installed.packages:
                if installed.name == self._package.name:
                    continue
                if installed.name in Provider.UNSAFE_PACKAGES:
                    # Never remove pip, setuptools etc.
                    continue
                if installed.name not in locked_names:
                    operations.append(Uninstall(installed))

        return sorted(
            operations, key=lambda o: (-o.priority, o.package.name, o.package.version,),
        )

    def solve_in_compatibility_mode(self, overrides, use_latest=None):
        locked = {}
        for package in self._locked.packages:
            locked[package.name] = DependencyPackage(package.to_dependency(), package)

        packages = []
        depths = []
        for override in overrides:
            self._provider.debug(
                "<comment>Retrying dependency resolution "
                "with the following overrides ({}).</comment>".format(override)
            )
            self._provider.set_overrides(override)
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

                    for dep in package.requires:
                        if dep not in pkg.requires:
                            pkg.requires.append(dep)

        return packages, depths

    def _solve(self, use_latest=None):
        if self._provider._overrides:
            self._overrides.append(self._provider._overrides)

        locked = {}
        for package in self._locked.packages:
            locked[package.name] = DependencyPackage(package.to_dependency(), package)

        try:
            result = resolve_version(
                self._package, self._provider, locked=locked, use_latest=use_latest
            )

            packages = result.packages
        except OverrideNeeded as e:
            return self.solve_in_compatibility_mode(e.overrides, use_latest=use_latest)
        except SolveFailure as e:
            raise SolverProblemError(e)

        results = dict(
            depth_first_search(
                PackageNode(self._package, packages), aggregate_package_nodes
            )
        )

        # Merging feature packages with base packages
        final_packages = []
        depths = []
        for package in packages:
            if package.features:
                for _package in packages:
                    if (
                        _package.name == package.name
                        and not _package.is_same_package_as(package)
                        and _package.version == package.version
                    ):
                        for dep in package.requires:
                            if dep.is_same_package_as(_package):
                                continue

                            if dep not in _package.requires:
                                _package.requires.append(dep)

                continue

            final_packages.append(package)
            depths.append(results[package])

        # Return the packages in their original order with associated depths
        return final_packages, depths


class DFSNode(object):
    def __init__(self, id, name, base_name):
        self.id = id
        self.name = name
        self.base_name = base_name

    def reachable(self):
        return []

    def visit(self, parents):
        pass

    def __str__(self):
        return str(self.id)


class VisitedState(enum.Enum):
    Unvisited = 0
    PartiallyVisited = 1
    Visited = 2


def depth_first_search(source, aggregator):
    back_edges = defaultdict(list)
    visited = {}
    topo_sorted_nodes = []

    dfs_visit(source, back_edges, visited, topo_sorted_nodes)

    # Combine the nodes by name
    combined_nodes = defaultdict(list)
    name_children = defaultdict(list)
    for node in topo_sorted_nodes:
        node.visit(back_edges[node.id])
        name_children[node.name].extend(node.reachable())
        combined_nodes[node.name].append(node)

    combined_topo_sorted_nodes = []
    for node in topo_sorted_nodes:
        if node.name in combined_nodes:
            combined_topo_sorted_nodes.append(combined_nodes.pop(node.name))

    results = [
        aggregator(nodes, name_children[nodes[0].name])
        for nodes in combined_topo_sorted_nodes
    ]
    return results


def dfs_visit(node, back_edges, visited, sorted_nodes):
    if visited.get(node.id, VisitedState.Unvisited) == VisitedState.Visited:
        return True
    if visited.get(node.id, VisitedState.Unvisited) == VisitedState.PartiallyVisited:
        # We have a circular dependency.
        # Since the dependencies are resolved we can
        # simply skip it because we already have it
        return True

    visited[node.id] = VisitedState.PartiallyVisited
    for neighbor in node.reachable():
        back_edges[neighbor.id].append(node)
        if not dfs_visit(neighbor, back_edges, visited, sorted_nodes):
            return False
    visited[node.id] = VisitedState.Visited
    sorted_nodes.insert(0, node)
    return True


class PackageNode(DFSNode):
    def __init__(
        self, package, packages, previous=None, previous_dep=None, dep=None,
    ):
        self.package = package
        self.packages = packages

        self.previous = previous
        self.previous_dep = previous_dep
        self.dep = dep
        self.depth = -1

        if not previous:
            self.category = "dev"
            self.optional = True
        else:
            self.category = dep.category
            self.optional = dep.is_optional()

        super(PackageNode, self).__init__(
            (package.complete_name, self.category, self.optional),
            package.complete_name,
            package.name,
        )

    def reachable(self):
        children = []  # type: List[PackageNode]

        if (
            self.previous_dep
            and self.previous_dep is not self.dep
            and self.previous_dep.name == self.dep.name
        ):
            return []

        for dependency in self.package.all_requires:
            if self.previous and self.previous.name == dependency.name:
                # We have a circular dependency.
                # Since the dependencies are resolved we can
                # simply skip it because we already have it
                # N.B. this only catches cycles of length 2;
                # dependency cycles in general are handled by the DFS traversal
                continue

            for pkg in self.packages:
                if pkg.complete_name == dependency.complete_name and (
                    dependency.constraint.allows(pkg.version)
                    or dependency.allows_prereleases()
                    and pkg.version.is_prerelease()
                    and dependency.constraint.allows(pkg.version.stable)
                ):
                    # If there is already a child with this name
                    # we merge the requirements
                    if any(
                        child.package.name == pkg.name
                        and child.category == dependency.category
                        for child in children
                    ):
                        continue

                    children.append(
                        PackageNode(
                            pkg,
                            self.packages,
                            self,
                            dependency,
                            self.dep or dependency,
                        )
                    )

        return children

    def visit(self, parents):
        # The root package, which has no parents, is defined as having depth -1
        # So that the root package's top-level dependencies have depth 0.
        self.depth = 1 + max(
            [
                parent.depth if parent.base_name != self.base_name else parent.depth - 1
                for parent in parents
            ]
            + [-2]
        )


def aggregate_package_nodes(nodes, children):
    package = nodes[0].package
    depth = max(node.depth for node in nodes)
    category = (
        "main" if any(node.category == "main" for node in children + nodes) else "dev"
    )
    optional = all(node.optional for node in children + nodes)
    for node in nodes:
        node.depth = depth
        node.category = category
        node.optional = optional
    package.category = category
    package.optional = optional
    return package, depth
