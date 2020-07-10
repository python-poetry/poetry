import time

from contextlib import contextmanager
from typing import Any
from typing import Dict
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
        remove_untracked=False,  # type: bool,
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

        graph = self._build_graph(self._package, packages)

        depths = []
        final_packages = []
        for package in packages:
            category, optional, depth = self._get_tags_for_package(package, graph)

            package.category = category
            package.optional = optional

            depths.append(depth)
            final_packages.append(package)

        return final_packages, depths

    def _build_graph(
        self, package, packages, previous=None, previous_dep=None, dep=None
    ):  # type: (...) -> Dict[str, Any]
        if not previous:
            category = "dev"
            optional = True
        else:
            category = dep.category
            optional = dep.is_optional() and not dep.is_activated()

        childrens = []  # type: List[Dict[str, Any]]
        graph = {
            "name": package.name,
            "category": category,
            "optional": optional,
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
                        continue

                    childrens.append(child_graph)

        return graph

    def _get_tags_for_package(self, package, graph, depth=0):
        categories = ["dev"]
        optionals = [True]
        _depths = [0]

        children = graph["children"]
        for child in children:
            if child["name"] == package.name:
                category = child["category"]
                optional = child["optional"]
                _depths.append(depth)
            else:
                (category, optional, _depth) = self._get_tags_for_package(
                    package, child, depth=depth + 1
                )

                _depths.append(_depth)

            categories.append(category)
            optionals.append(optional)

        if "main" in categories:
            category = "main"
        else:
            category = "dev"

        optional = all(optionals)

        depth = max(*(_depths + [0]))

        return category, optional, depth
