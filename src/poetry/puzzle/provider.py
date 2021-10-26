import logging
import os
import re
import tempfile
import time
import urllib.parse

from contextlib import contextmanager
from pathlib import Path
from tempfile import mkdtemp
from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
from typing import Set
from typing import Union

from cleo.ui.progress_indicator import ProgressIndicator
from poetry.core.packages.utils.utils import get_python_constraint_from_marker
from poetry.core.semver.version import Version
from poetry.core.vcs.git import Git
from poetry.core.version.markers import MarkerUnion

from poetry.inspection.info import PackageInfo
from poetry.inspection.info import PackageInfoError
from poetry.mixology.incompatibility import Incompatibility
from poetry.mixology.incompatibility_cause import DependencyCause
from poetry.mixology.incompatibility_cause import PythonCause
from poetry.mixology.term import Term
from poetry.packages import DependencyPackage
from poetry.packages.package_collection import PackageCollection
from poetry.puzzle.exceptions import OverrideNeeded
from poetry.utils.helpers import download_file
from poetry.utils.helpers import safe_rmtree


if TYPE_CHECKING:
    from poetry.core.packages.dependency import Dependency
    from poetry.core.packages.directory_dependency import DirectoryDependency
    from poetry.core.packages.file_dependency import FileDependency
    from poetry.core.packages.package import Package
    from poetry.core.packages.url_dependency import URLDependency
    from poetry.core.packages.vcs_dependency import VCSDependency

    from poetry.repositories import Pool
    from poetry.utils.env import Env


logger = logging.getLogger(__name__)


class Indicator(ProgressIndicator):
    def _formatter_elapsed(self) -> str:
        elapsed = time.time() - self._start_time

        return f"{elapsed:.1f}s"


class Provider:

    UNSAFE_PACKAGES: Set[str] = set()

    def __init__(
        self, package: "Package", pool: "Pool", io: Any, env: Optional["Env"] = None
    ) -> None:
        self._package = package
        self._pool = pool
        self._io = io
        self._env = env
        self._python_constraint = package.python_constraint
        self._search_for: Dict["Dependency", List["Package"]] = {}
        self._is_debugging = self._io.is_debug() or self._io.is_very_verbose()
        self._in_progress = False
        self._overrides: Dict = {}
        self._deferred_cache: Dict["Dependency", "Package"] = {}
        self._load_deferred = True

    @property
    def pool(self) -> "Pool":
        return self._pool

    def is_debugging(self) -> bool:
        return self._is_debugging

    def set_overrides(self, overrides: Dict) -> None:
        self._overrides = overrides

    def load_deferred(self, load_deferred: bool) -> None:
        self._load_deferred = load_deferred

    @contextmanager
    def use_environment(self, env: "Env") -> Iterator["Provider"]:
        original_env = self._env
        original_python_constraint = self._python_constraint

        self._env = env
        self._python_constraint = Version.parse(env.marker_env["python_full_version"])

        yield self

        self._env = original_env
        self._python_constraint = original_python_constraint

    def search_for(
        self,
        dependency: Union[
            "Dependency",
            "VCSDependency",
            "FileDependency",
            "DirectoryDependency",
            "URLDependency",
        ],
    ) -> List["DependencyPackage"]:
        """
        Search for the specifications that match the given dependency.

        The specifications in the returned list will be considered in reverse
        order, so the latest version ought to be last.
        """
        if dependency.is_root:
            return PackageCollection(dependency, [self._package])

        for constraint in self._search_for:
            if (
                constraint.is_same_package_as(dependency)
                and constraint.constraint.intersect(dependency.constraint)
                == dependency.constraint
            ):
                packages = [
                    p
                    for p in self._search_for[constraint]
                    if dependency.constraint.allows(p.version)
                ]

                packages.sort(
                    key=lambda p: (
                        not p.is_prerelease() and not dependency.allows_prereleases(),
                        p.version,
                    ),
                    reverse=True,
                )

                return PackageCollection(dependency, packages)

        if dependency.is_vcs():
            packages = self.search_for_vcs(dependency)
        elif dependency.is_file():
            packages = self.search_for_file(dependency)
        elif dependency.is_directory():
            packages = self.search_for_directory(dependency)
        elif dependency.is_url():
            packages = self.search_for_url(dependency)
        else:
            packages = self._pool.find_packages(dependency)

            packages.sort(
                key=lambda p: (
                    not p.is_prerelease() and not dependency.allows_prereleases(),
                    p.version,
                ),
                reverse=True,
            )

        self._search_for[dependency] = packages

        return PackageCollection(dependency, packages)

    def search_for_vcs(self, dependency: "VCSDependency") -> List["Package"]:
        """
        Search for the specifications that match the given VCS dependency.

        Basically, we clone the repository in a temporary directory
        and get the information we need by checking out the specified reference.
        """
        if dependency in self._deferred_cache:
            return [self._deferred_cache[dependency]]

        package = self.get_package_from_vcs(
            dependency.vcs,
            dependency.source,
            branch=dependency.branch,
            tag=dependency.tag,
            rev=dependency.rev,
            name=dependency.name,
        )
        package.develop = dependency.develop

        dependency._constraint = package.version
        dependency._pretty_constraint = package.version.text
        dependency._source_resolved_reference = package.source_resolved_reference

        dependency._source_reference = package.source_reference
        dependency._source_resolved_reference = package.source_resolved_reference

        if hasattr(package, "source_subdirectory") and hasattr(
            dependency, "_source_subdirectory"
        ):
            # this is supported only for poetry-core >= 1.1.0a7
            dependency._source_subdirectory = package.source_subdirectory

        self._deferred_cache[dependency] = package

        return [package]

    @classmethod
    def get_package_from_vcs(
        cls,
        vcs: str,
        url: str,
        branch: Optional[str] = None,
        tag: Optional[str] = None,
        rev: Optional[str] = None,
        name: Optional[str] = None,
    ) -> "Package":
        if vcs != "git":
            raise ValueError(f"Unsupported VCS dependency {vcs}")

        suffix = url.split("/")[-1].rstrip(".git")
        tmp_dir = Path(mkdtemp(prefix=f"pypoetry-git-{suffix}"))

        try:
            git = Git()
            git.clone(url, tmp_dir)
            reference = branch or tag or rev
            if reference is not None:
                git.checkout(reference, tmp_dir)
            else:
                reference = "HEAD"

            revision = git.rev_parse(reference, tmp_dir).strip()

            package = cls.get_package_from_directory(tmp_dir, name=name)
            package._source_type = "git"
            package._source_url = url
            package._source_reference = reference
            package._source_resolved_reference = revision
        except Exception:
            raise
        finally:
            safe_rmtree(str(tmp_dir))

        return package

    def search_for_file(self, dependency: "FileDependency") -> List["Package"]:
        if dependency in self._deferred_cache:
            dependency, _package = self._deferred_cache[dependency]

            package = _package.clone()
        else:
            package = self.get_package_from_file(dependency.full_path)

            dependency._constraint = package.version
            dependency._pretty_constraint = package.version.text

            self._deferred_cache[dependency] = (dependency, package)

        if dependency.name != package.name:
            # For now, the dependency's name must match the actual package's name
            raise RuntimeError(
                f"The dependency name for {dependency.name} does not match the actual package's name: {package.name}"
            )

        if dependency.base is not None:
            package.root_dir = dependency.base

        package.files = [
            {"file": dependency.path.name, "hash": "sha256:" + dependency.hash()}
        ]

        return [package]

    @classmethod
    def get_package_from_file(cls, file_path: Path) -> "Package":
        try:
            package = PackageInfo.from_path(path=file_path).to_package(
                root_dir=file_path
            )
        except PackageInfoError:
            raise RuntimeError(
                f"Unable to determine package info from path: {file_path}"
            )

        return package

    def search_for_directory(
        self, dependency: "DirectoryDependency"
    ) -> List["Package"]:
        if dependency in self._deferred_cache:
            dependency, _package = self._deferred_cache[dependency]

            package = _package.clone()
        else:
            package = self.get_package_from_directory(
                dependency.full_path, name=dependency.name
            )

            dependency._constraint = package.version
            dependency._pretty_constraint = package.version.text

            self._deferred_cache[dependency] = (dependency, package)

        package.develop = dependency.develop

        if dependency.base is not None:
            package.root_dir = dependency.base

        return [package]

    @classmethod
    def get_package_from_directory(
        cls, directory: Path, name: Optional[str] = None
    ) -> "Package":
        package = PackageInfo.from_directory(path=directory).to_package(
            root_dir=directory
        )

        if name and name != package.name:
            # For now, the dependency's name must match the actual package's name
            raise RuntimeError(
                f"The dependency name for {name} does not match the actual package's name: {package.name}"
            )

        return package

    def search_for_url(self, dependency: "URLDependency") -> List["Package"]:
        if dependency in self._deferred_cache:
            return [self._deferred_cache[dependency]]

        package = self.get_package_from_url(dependency.url)

        if dependency.name != package.name:
            # For now, the dependency's name must match the actual package's name
            raise RuntimeError(
                f"The dependency name for {dependency.name} does not match the actual package's name: {package.name}"
            )

        for extra in dependency.extras:
            if extra in package.extras:
                for dep in package.extras[extra]:
                    dep.activate()

                for extra_dep in package.extras[extra]:
                    package.add_dependency(extra_dep)

        dependency._constraint = package.version
        dependency._pretty_constraint = package.version.text

        self._deferred_cache[dependency] = package

        return [package]

    @classmethod
    def get_package_from_url(cls, url: str) -> "Package":
        file_name = os.path.basename(urllib.parse.urlparse(url).path)
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / file_name
            download_file(url, str(dest))
            package = cls.get_package_from_file(dest)

        package._source_type = "url"
        package._source_url = url

        return package

    def incompatibilities_for(
        self, package: DependencyPackage
    ) -> List[Incompatibility]:
        """
        Returns incompatibilities that encapsulate a given package's dependencies,
        or that it can't be safely selected.

        If multiple subsequent versions of this package have the same
        dependencies, this will return incompatibilities that reflect that. It
        won't return incompatibilities that have already been returned by a
        previous call to _incompatibilities_for().
        """
        if package.is_root():
            dependencies = package.all_requires
        else:
            dependencies = package.requires

            if not package.python_constraint.allows_all(self._python_constraint):
                transitive_python_constraint = get_python_constraint_from_marker(
                    package.dependency.transitive_marker
                )
                intersection = package.python_constraint.intersect(
                    transitive_python_constraint
                )
                difference = transitive_python_constraint.difference(intersection)

                # The difference is only relevant if it intersects
                # the root package python constraint
                difference = difference.intersect(self._python_constraint)
                if (
                    transitive_python_constraint.is_any()
                    or self._python_constraint.intersect(
                        package.dependency.python_constraint
                    ).is_empty()
                    or intersection.is_empty()
                    or not difference.is_empty()
                ):
                    return [
                        Incompatibility(
                            [Term(package.to_dependency(), True)],
                            PythonCause(
                                package.python_versions, str(self._python_constraint)
                            ),
                        )
                    ]

        _dependencies = [
            dep
            for dep in dependencies
            if dep.name not in self.UNSAFE_PACKAGES
            and self._python_constraint.allows_any(dep.python_constraint)
            and (not self._env or dep.marker.validate(self._env.marker_env))
        ]

        overrides = self._overrides.get(package, {})
        dependencies = []
        overridden = []
        for dep in _dependencies:
            if dep.name in overrides:
                if dep.name in overridden:
                    continue

                dependencies.append(overrides[dep.name])
                overridden.append(dep.name)

                continue

            dependencies.append(dep)

        return [
            Incompatibility(
                [Term(package.to_dependency(), True), Term(dep, False)],
                DependencyCause(),
            )
            for dep in dependencies
        ]

    def complete_package(self, package: DependencyPackage) -> DependencyPackage:
        if package.is_root():
            package = package.clone()
            requires = package.all_requires
        elif not package.is_root() and package.source_type not in {
            "directory",
            "file",
            "url",
            "git",
        }:
            package = DependencyPackage(
                package.dependency,
                self._pool.package(
                    package.name,
                    package.version.text,
                    extras=list(package.dependency.extras),
                    repository=package.dependency.source_name,
                ),
            )
            requires = package.requires
        else:
            requires = package.requires

        if self._load_deferred:
            # Retrieving constraints for deferred dependencies
            for r in requires:
                if r.is_directory():
                    self.search_for_directory(r)
                elif r.is_file():
                    self.search_for_file(r)
                elif r.is_vcs():
                    self.search_for_vcs(r)
                elif r.is_url():
                    self.search_for_url(r)

        optional_dependencies = []
        _dependencies = []

        # If some extras/features were required, we need to
        # add a special dependency representing the base package
        # to the current package
        if package.dependency.extras:
            for extra in package.dependency.extras:
                if extra not in package.extras:
                    continue

                optional_dependencies += [d.name for d in package.extras[extra]]

            package = package.with_features(list(package.dependency.extras))
            _dependencies.append(package.without_features().to_dependency())

        for dep in requires:
            if not self._python_constraint.allows_any(dep.python_constraint):
                continue

            if dep.name in self.UNSAFE_PACKAGES:
                continue

            if self._env and not dep.marker.validate(self._env.marker_env):
                continue

            if not package.is_root() and (
                (dep.is_optional() and dep.name not in optional_dependencies)
                or (
                    dep.in_extras
                    and not set(dep.in_extras).intersection(package.dependency.extras)
                )
            ):
                continue

            _dependencies.append(dep)

        overrides = self._overrides.get(package, {})
        dependencies = []
        overridden = []
        for dep in _dependencies:
            if dep.name in overrides:
                if dep.name in overridden:
                    continue

                dependencies.append(overrides[dep.name])
                overridden.append(dep.name)

                continue

            dependencies.append(dep)

        # Searching for duplicate dependencies
        #
        # If the duplicate dependencies have the same constraint,
        # the requirements will be merged.
        #
        # For instance:
        #   - enum34; python_version=="2.7"
        #   - enum34; python_version=="3.3"
        #
        # will become:
        #   - enum34; python_version=="2.7" or python_version=="3.3"
        #
        # If the duplicate dependencies have different constraints
        # we have to split the dependency graph.
        #
        # An example of this is:
        #   - pypiwin32 (220); sys_platform == "win32" and python_version >= "3.6"
        #   - pypiwin32 (219); sys_platform == "win32" and python_version < "3.6"
        duplicates: Dict[str, List["Dependency"]] = {}
        for dep in dependencies:
            if dep.complete_name not in duplicates:
                duplicates[dep.complete_name] = []

            duplicates[dep.complete_name].append(dep)

        dependencies = []
        for dep_name, deps in duplicates.items():
            if len(deps) == 1:
                dependencies.append(deps[0])
                continue

            self.debug(f"<debug>Duplicate dependencies for {dep_name}</debug>")

            # Regrouping by constraint
            by_constraint: Dict[str, List["Dependency"]] = {}
            for dep in deps:
                if dep.constraint not in by_constraint:
                    by_constraint[dep.constraint] = []

                by_constraint[dep.constraint].append(dep)

            # We merge by constraint
            for constraint, _deps in by_constraint.items():
                new_markers = []
                for dep in _deps:
                    marker = dep.marker.without_extras()
                    if marker.is_any():
                        # No marker or only extras
                        continue

                    new_markers.append(marker)

                if not new_markers:
                    continue

                dep = _deps[0]
                dep.marker = dep.marker.union(MarkerUnion(*new_markers))
                by_constraint[constraint] = [dep]

                continue

            if len(by_constraint) == 1:
                self.debug(f"<debug>Merging requirements for {deps[0]!s}</debug>")
                dependencies.append(list(by_constraint.values())[0][0])
                continue

            # We leave dependencies as-is if they have the same
            # python/platform constraints.
            # That way the resolver will pickup the conflict
            # and display a proper error.
            _deps = [value[0] for value in by_constraint.values()]
            seen = set()
            for _dep in _deps:
                pep_508_dep = _dep.to_pep_508(False)
                if ";" not in pep_508_dep:
                    _requirements = ""
                else:
                    _requirements = pep_508_dep.split(";")[1].strip()

                if _requirements not in seen:
                    seen.add(_requirements)

            if len(_deps) != len(seen):
                for _dep in _deps:
                    dependencies.append(_dep)

                continue

            # At this point, we raise an exception that will
            # tell the solver to make new resolutions with specific overrides.
            #
            # For instance, if the foo (1.2.3) package has the following dependencies:
            #   - bar (>=2.0) ; python_version >= "3.6"
            #   - bar (<2.0) ; python_version < "3.6"
            #
            # then the solver will need to make two new resolutions
            # with the following overrides:
            #   - {<Package foo (1.2.3): {"bar": <Dependency bar (>=2.0)>}
            #   - {<Package foo (1.2.3): {"bar": <Dependency bar (<2.0)>}
            _deps = [_dep[0] for _dep in by_constraint.values()]

            def fmt_warning(d: "Dependency") -> str:
                marker = d.marker if not d.marker.is_any() else "*"
                return (
                    f"<c1>{d.name}</c1> <fg=default>(<c2>{d.pretty_constraint}</c2>)</> "
                    f"with markers <b>{marker}</b>"
                )

            warnings = ", ".join(fmt_warning(d) for d in _deps[:-1])
            warnings += f" and {fmt_warning(_deps[-1])}"
            self.debug(
                f"<warning>Different requirements found for {warnings}.</warning>"
            )

            # We need to check if one of the duplicate dependencies
            # has no markers. If there is one, we need to change its
            # environment markers to the inverse of the union of the
            # other dependencies markers.
            # For instance, if we have the following dependencies:
            #   - ipython
            #   - ipython (1.2.4) ; implementation_name == "pypy"
            #
            # the marker for `ipython` will become `implementation_name != "pypy"`.
            #
            # Further, we have to merge the constraints of the requirements
            # without markers into the constraints of the requirements with markers.
            # for instance, if we have the following dependencies:
            #   - foo (>= 1.2)
            #   - foo (!= 1.2.1) ; python == 3.10
            #
            # the constraint for the second entry will become (!= 1.2.1, >= 1.2)
            any_markers_dependencies = [d for d in _deps if d.marker.is_any()]
            other_markers_dependencies = [d for d in _deps if not d.marker.is_any()]

            if any_markers_dependencies:
                marker = other_markers_dependencies[0].marker
                for other_dep in other_markers_dependencies[1:]:
                    marker = marker.union(other_dep.marker)

                inverted_marker = marker.invert()
                for dep_any in any_markers_dependencies:
                    dep_any.marker = inverted_marker
                    for dep_other in other_markers_dependencies:
                        dep_other.set_constraint(
                            dep_other.constraint.intersect(dep_any.constraint)
                        )
                        # TODO: Setting _pretty_constraint can be removed once the following issue has been fixed
                        # https://github.com/python-poetry/poetry/issues/4589
                        dep_other._pretty_constraint = str(dep_other.constraint)

            overrides = []
            for _dep in _deps:
                current_overrides = self._overrides.copy()
                package_overrides = current_overrides.get(package, {}).copy()
                package_overrides.update({_dep.name: _dep})
                current_overrides.update({package: package_overrides})
                overrides.append(current_overrides)

            raise OverrideNeeded(*overrides)

        # Modifying dependencies as needed
        clean_dependencies = []
        for dep in dependencies:
            if not package.dependency.transitive_marker.without_extras().is_any():
                marker_intersection = (
                    package.dependency.transitive_marker.without_extras().intersect(
                        dep.marker.without_extras()
                    )
                )
                if marker_intersection.is_empty():
                    # The dependency is not needed, since the markers specified
                    # for the current package selection are not compatible with
                    # the markers for the current dependency, so we skip it
                    continue

                dep.transitive_marker = marker_intersection

            if not package.dependency.python_constraint.is_any():
                python_constraint_intersection = dep.python_constraint.intersect(
                    package.dependency.python_constraint
                )
                if python_constraint_intersection.is_empty():
                    # This dependency is not needed under current python constraint.
                    continue
                dep.transitive_python_versions = str(python_constraint_intersection)

            clean_dependencies.append(dep)

        package = DependencyPackage(
            package.dependency, package.with_dependency_groups([], only=True)
        )

        for dep in clean_dependencies:
            package.add_dependency(dep)

        return package

    def debug(self, message: str, depth: int = 0) -> None:
        if not (self._io.is_very_verbose() or self._io.is_debug()):
            return

        if message.startswith("fact:"):
            if "depends on" in message:
                m = re.match(r"fact: (.+?) depends on (.+?) \((.+?)\)", message)
                if m is None:
                    raise ValueError(f"Unable to parse fact: {message}")
                m2 = re.match(r"(.+?) \((.+?)\)", m.group(1))
                if m2:
                    name = m2.group(1)
                    version = f" (<c2>{m2.group(2)}</c2>)"
                else:
                    name = m.group(1)
                    version = ""

                message = (
                    f"<fg=blue>fact</>: <c1>{name}</c1>{version} "
                    f"depends on <c1>{m.group(2)}</c1> (<c2>{m.group(3)}</c2>)"
                )
            elif " is " in message:
                message = re.sub(
                    "fact: (.+) is (.+)",
                    "<fg=blue>fact</>: <c1>\\1</c1> is <c2>\\2</c2>",
                    message,
                )
            else:
                message = re.sub(
                    r"(?<=: )(.+?) \((.+?)\)", "<c1>\\1</c1> (<c2>\\2</c2>)", message
                )
                message = f"<fg=blue>fact</>: {message.split('fact: ')[1]}"
        elif message.startswith("selecting "):
            message = re.sub(
                r"selecting (.+?) \((.+?)\)",
                "<fg=blue>selecting</> <c1>\\1</c1> (<c2>\\2</c2>)",
                message,
            )
        elif message.startswith("derived:"):
            m = re.match(r"derived: (.+?) \((.+?)\)$", message)
            if m:
                message = f"<fg=blue>derived</>: <c1>{m.group(1)}</c1> (<c2>{m.group(2)}</c2>)"
            else:
                message = (
                    f"<fg=blue>derived</>: <c1>{message.split('derived: ')[1]}</c1>"
                )
        elif message.startswith("conflict:"):
            m = re.match(r"conflict: (.+?) depends on (.+?) \((.+?)\)", message)
            if m:
                m2 = re.match(r"(.+?) \((.+?)\)", m.group(1))
                if m2:
                    name = m2.group(1)
                    version = f" (<c2>{m2.group(2)}</c2>)"
                else:
                    name = m.group(1)
                    version = ""

                message = (
                    f"<fg=red;options=bold>conflict</>: <c1>{name}</c1>{version} "
                    f"depends on <c1>{m.group(2)}</c1> (<c2>{m.group(3)}</c2>)"
                )
            else:
                message = f"<fg=red;options=bold>conflict</>: {message.split('conflict: ')[1]}"

        message = message.replace("! ", "<error>!</error> ")

        if self.is_debugging():
            debug_info = str(message)
            debug_info = (
                "\n".join(
                    [
                        f"<debug>{str(depth).rjust(4)}:</debug> {s}"
                        for s in debug_info.split("\n")
                    ]
                )
                + "\n"
            )

            self._io.write(debug_info)

    @contextmanager
    def progress(self) -> Iterator[None]:
        if not self._io.output.is_decorated() or self.is_debugging():
            self._io.write_line("Resolving dependencies...")
            yield
        else:
            indicator = Indicator(self._io, "{message} <debug>({elapsed:2s})</debug>")

            with indicator.auto(
                "<info>Resolving dependencies...</info>",
                "<info>Resolving dependencies...</info>",
            ):
                yield

        self._in_progress = False
