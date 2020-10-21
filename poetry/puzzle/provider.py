import logging
import os
import re
import time

from contextlib import contextmanager
from tempfile import mkdtemp
from typing import Any
from typing import List
from typing import Optional

from clikit.ui.components import ProgressIndicator

from poetry.core.packages import Dependency
from poetry.core.packages import DirectoryDependency
from poetry.core.packages import FileDependency
from poetry.core.packages import Package
from poetry.core.packages import URLDependency
from poetry.core.packages import VCSDependency
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
from poetry.repositories import Pool
from poetry.utils._compat import OrderedDict
from poetry.utils._compat import Path
from poetry.utils._compat import urlparse
from poetry.utils.env import Env
from poetry.utils.helpers import download_file
from poetry.utils.helpers import safe_rmtree
from poetry.utils.helpers import temporary_directory


logger = logging.getLogger(__name__)


class Indicator(ProgressIndicator):
    def _formatter_elapsed(self):
        elapsed = time.time() - self._start_time

        return "{:.1f}s".format(elapsed)


class Provider:

    UNSAFE_PACKAGES = {"setuptools", "distribute", "pip", "wheel"}

    def __init__(
        self, package, pool, io, env=None
    ):  # type: (Package, Pool, Any, Optional[Env]) -> None
        self._package = package
        self._pool = pool
        self._io = io
        self._env = env
        self._python_constraint = package.python_constraint
        self._search_for = {}
        self._is_debugging = self._io.is_debug() or self._io.is_very_verbose()
        self._in_progress = False
        self._overrides = {}
        self._deferred_cache = {}
        self._load_deferred = True

    @property
    def pool(self):  # type: () -> Pool
        return self._pool

    def is_debugging(self):
        return self._is_debugging

    def set_overrides(self, overrides):
        self._overrides = overrides

    def load_deferred(self, load_deferred):  # type: (bool) -> None
        self._load_deferred = load_deferred

    @contextmanager
    def use_environment(self, env):  # type: (Env) -> Provider
        original_env = self._env
        original_python_constraint = self._python_constraint

        self._env = env
        self._python_constraint = Version.parse(env.marker_env["python_full_version"])

        yield self

        self._env = original_env
        self._python_constraint = original_python_constraint

    def search_for(self, dependency):  # type: (Dependency) -> List[Package]
        """
        Search for the specifications that match the given dependency.

        The specifications in the returned list will be considered in reverse
        order, so the latest version ought to be last.
        """
        if dependency.is_root:
            return PackageCollection(dependency, [self._package])

        for constraint in self._search_for.keys():
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

    def search_for_vcs(self, dependency):  # type: (VCSDependency) -> List[Package]
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

        self._deferred_cache[dependency] = package

        return [package]

    @classmethod
    def get_package_from_vcs(
        cls, vcs, url, branch=None, tag=None, rev=None, name=None
    ):  # type: (str, str, Optional[str], Optional[str]) -> Package
        if vcs != "git":
            raise ValueError("Unsupported VCS dependency {}".format(vcs))

        tmp_dir = Path(
            mkdtemp(prefix="pypoetry-git-{}".format(url.split("/")[-1].rstrip(".git")))
        )

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

    def search_for_file(self, dependency):  # type: (FileDependency) -> List[Package]
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
                "The dependency name for {} does not match the actual package's name: {}".format(
                    dependency.name, package.name
                )
            )

        if dependency.base is not None:
            package.root_dir = dependency.base

        package.files = [
            {"file": dependency.path.name, "hash": "sha256:" + dependency.hash()}
        ]

        return [package]

    @classmethod
    def get_package_from_file(cls, file_path):  # type: (Path) -> Package
        try:
            package = PackageInfo.from_path(path=file_path).to_package(
                root_dir=file_path
            )
        except PackageInfoError:
            raise RuntimeError(
                "Unable to determine package info from path: {}".format(file_path)
            )

        return package

    def search_for_directory(
        self, dependency
    ):  # type: (DirectoryDependency) -> List[Package]
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
        cls, directory, name=None
    ):  # type: (Path, Optional[str]) -> Package
        package = PackageInfo.from_directory(path=directory).to_package(
            root_dir=directory
        )

        if name and name != package.name:
            # For now, the dependency's name must match the actual package's name
            raise RuntimeError(
                "The dependency name for {} does not match the actual package's name: {}".format(
                    name, package.name
                )
            )

        return package

    def search_for_url(self, dependency):  # type: (URLDependency) -> List[Package]
        if dependency in self._deferred_cache:
            return [self._deferred_cache[dependency]]

        package = self.get_package_from_url(dependency.url)

        if dependency.name != package.name:
            # For now, the dependency's name must match the actual package's name
            raise RuntimeError(
                "The dependency name for {} does not match the actual package's name: {}".format(
                    dependency.name, package.name
                )
            )

        for extra in dependency.extras:
            if extra in package.extras:
                for dep in package.extras[extra]:
                    dep.activate()

                package.requires += package.extras[extra]

        dependency._constraint = package.version
        dependency._pretty_constraint = package.version.text

        self._deferred_cache[dependency] = package

        return [package]

    @classmethod
    def get_package_from_url(cls, url):  # type: (str) -> Package
        with temporary_directory() as temp_dir:
            temp_dir = Path(temp_dir)
            file_name = os.path.basename(urlparse.urlparse(url).path)
            download_file(url, str(temp_dir / file_name))

            package = cls.get_package_from_file(temp_dir / file_name)

        package._source_type = "url"
        package._source_url = url

        return package

    def incompatibilities_for(
        self, package
    ):  # type: (DependencyPackage) -> List[Incompatibility]
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

    def complete_package(
        self, package
    ):  # type: (DependencyPackage) -> DependencyPackage

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

            if not package.is_root():
                if (dep.is_optional() and dep.name not in optional_dependencies) or (
                    dep.in_extras
                    and not set(dep.in_extras).intersection(package.dependency.extras)
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
        duplicates = OrderedDict()
        for dep in dependencies:
            if dep.name not in duplicates:
                duplicates[dep.name] = []

            duplicates[dep.name].append(dep)

        dependencies = []
        for dep_name, deps in duplicates.items():
            if len(deps) == 1:
                dependencies.append(deps[0])
                continue

            self.debug("<debug>Duplicate dependencies for {}</debug>".format(dep_name))

            # Regrouping by constraint
            by_constraint = OrderedDict()
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
                self.debug(
                    "<debug>Merging requirements for {}</debug>".format(str(deps[0]))
                )
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
            markers = []
            for constraint, _deps in by_constraint.items():
                markers.append(_deps[0].marker)

            _deps = [_dep[0] for _dep in by_constraint.values()]
            self.debug(
                "<warning>Different requirements found for {}.</warning>".format(
                    ", ".join(
                        "<c1>{}</c1> <fg=default>(<c2>{}</c2>)</> with markers <b>{}</b>".format(
                            d.name,
                            d.pretty_constraint,
                            d.marker if not d.marker.is_any() else "*",
                        )
                        for d in _deps[:-1]
                    )
                    + " and "
                    + "<c1>{}</c1> <fg=default>(<c2>{}</c2>)</> with markers <b>{}</b>".format(
                        _deps[-1].name,
                        _deps[-1].pretty_constraint,
                        _deps[-1].marker if not _deps[-1].marker.is_any() else "*",
                    )
                )
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
            any_markers_dependencies = [d for d in _deps if d.marker.is_any()]
            other_markers_dependencies = [d for d in _deps if not d.marker.is_any()]

            if any_markers_dependencies:
                marker = other_markers_dependencies[0].marker
                for other_dep in other_markers_dependencies[1:]:
                    marker = marker.union(other_dep.marker)

                for i, d in enumerate(_deps):
                    if d.marker.is_any():
                        _deps[i].marker = marker.invert()

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
                marker_intersection = package.dependency.transitive_marker.without_extras().intersect(
                    dep.marker.without_extras()
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

        package.requires = clean_dependencies

        return package

    def debug(self, message, depth=0):
        if not (self._io.is_very_verbose() or self._io.is_debug()):
            return

        if message.startswith("fact:"):
            if "depends on" in message:
                m = re.match(r"fact: (.+?) depends on (.+?) \((.+?)\)", message)
                m2 = re.match(r"(.+?) \((.+?)\)", m.group(1))
                if m2:
                    name = m2.group(1)
                    version = " (<c2>{}</c2>)".format(m2.group(2))
                else:
                    name = m.group(1)
                    version = ""

                message = (
                    "<fg=blue>fact</>: <c1>{}</c1>{} "
                    "depends on <c1>{}</c1> (<c2>{}</c2>)".format(
                        name, version, m.group(2), m.group(3)
                    )
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
                message = "<fg=blue>fact</>: {}".format(message.split("fact: ")[1])
        elif message.startswith("selecting "):
            message = re.sub(
                r"selecting (.+?) \((.+?)\)",
                "<fg=blue>selecting</> <c1>\\1</c1> (<c2>\\2</c2>)",
                message,
            )
        elif message.startswith("derived:"):
            m = re.match(r"derived: (.+?) \((.+?)\)$", message)
            if m:
                message = "<fg=blue>derived</>: <c1>{}</c1> (<c2>{}</c2>)".format(
                    m.group(1), m.group(2)
                )
            else:
                message = "<fg=blue>derived</>: <c1>{}</c1>".format(
                    message.split("derived: ")[1]
                )
        elif message.startswith("conflict:"):
            m = re.match(r"conflict: (.+?) depends on (.+?) \((.+?)\)", message)
            if m:
                m2 = re.match(r"(.+?) \((.+?)\)", m.group(1))
                if m2:
                    name = m2.group(1)
                    version = " (<c2>{}</c2>)".format(m2.group(2))
                else:
                    name = m.group(1)
                    version = ""

                message = (
                    "<fg=red;options=bold>conflict</>: <c1>{}</c1>{} "
                    "depends on <c1>{}</c1> (<c2>{}</c2>)".format(
                        name, version, m.group(2), m.group(3)
                    )
                )
            else:
                message = "<fg=red;options=bold>conflict</>: {}".format(
                    message.split("conflict: ")[1]
                )

        message = message.replace("! ", "<error>!</error> ")

        if self.is_debugging():
            debug_info = str(message)
            debug_info = (
                "\n".join(
                    [
                        "<debug>{}:</debug> {}".format(str(depth).rjust(4), s)
                        for s in debug_info.split("\n")
                    ]
                )
                + "\n"
            )

            self._io.write(debug_info)

    @contextmanager
    def progress(self):
        if not self._io.output.supports_ansi() or self.is_debugging():
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
