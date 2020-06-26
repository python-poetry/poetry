import glob
import logging
import os
import re
import time

from contextlib import contextmanager
from tempfile import mkdtemp
from typing import Any
from typing import List
from typing import Optional

import pkginfo

from clikit.ui.components import ProgressIndicator

from poetry.factory import Factory
from poetry.mixology.incompatibility import Incompatibility
from poetry.mixology.incompatibility_cause import DependencyCause
from poetry.mixology.incompatibility_cause import PythonCause
from poetry.mixology.term import Term
from poetry.packages import Dependency
from poetry.packages import DependencyPackage
from poetry.packages import DirectoryDependency
from poetry.packages import FileDependency
from poetry.packages import Package
from poetry.packages import PackageCollection
from poetry.packages import URLDependency
from poetry.packages import VCSDependency
from poetry.packages import dependency_from_pep_508
from poetry.packages.utils.utils import get_python_constraint_from_marker
from poetry.repositories import Pool
from poetry.utils._compat import PY35
from poetry.utils._compat import OrderedDict
from poetry.utils._compat import Path
from poetry.utils._compat import urlparse
from poetry.utils.env import EnvCommandError
from poetry.utils.env import EnvManager
from poetry.utils.env import VirtualEnv
from poetry.utils.helpers import parse_requires
from poetry.utils.helpers import safe_rmtree
from poetry.utils.helpers import temporary_directory
from poetry.utils.inspector import Inspector
from poetry.utils.setup_reader import SetupReader
from poetry.utils.toml_file import TomlFile
from poetry.vcs.git import Git
from poetry.version.markers import MarkerUnion

from .exceptions import CompatibilityError


logger = logging.getLogger(__name__)


class Indicator(ProgressIndicator):
    def _formatter_elapsed(self):
        elapsed = time.time() - self._start_time

        return "{:.1f}s".format(elapsed)


class Provider:

    UNSAFE_PACKAGES = {"setuptools", "distribute", "pip"}

    def __init__(self, package, pool, io):  # type: (Package, Pool, Any) -> None
        self._package = package
        self._pool = pool
        self._io = io
        self._inspector = Inspector()
        self._python_constraint = package.python_constraint
        self._search_for = {}
        self._is_debugging = self._io.is_debug() or self._io.is_very_verbose()
        self._in_progress = False
        self._deferred_cache = {}

    @property
    def pool(self):  # type: () -> Pool
        return self._pool

    @property
    def name_for_explicit_dependency_source(self):  # type: () -> str
        return "pyproject.toml"

    @property
    def name_for_locking_dependency_source(self):  # type: () -> str
        return "poetry.lock"

    def is_debugging(self):
        return self._is_debugging

    def name_for(self, dependency):  # type: (Dependency) -> str
        """
        Returns the name for the given dependency.
        """
        return dependency.name

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
                constraint.name == dependency.name
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
            constraint = dependency.constraint

            packages = self._pool.find_packages(
                dependency.name,
                constraint,
                extras=dependency.extras,
                allow_prereleases=dependency.allows_prereleases(),
                repository=dependency.source_name,
            )

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
            dependency.reference,
            name=dependency.name,
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
    def get_package_from_vcs(
        cls, vcs, url, reference=None, name=None
    ):  # type: (str, str, Optional[str], Optional[str]) -> Package
        if vcs != "git":
            raise ValueError("Unsupported VCS dependency {}".format(vcs))

        tmp_dir = Path(
            mkdtemp(prefix="pypoetry-git-{}".format(url.split("/")[-1].rstrip(".git")))
        )

        try:
            git = Git()
            git.clone(url, tmp_dir)
            if reference is not None:
                git.checkout(reference, tmp_dir)
            else:
                reference = "HEAD"

            revision = git.rev_parse(reference, tmp_dir).strip()

            package = cls.get_package_from_directory(tmp_dir, name=name)

            package.source_type = "git"
            package.source_url = url
            package.source_reference = revision
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

        package.source_url = dependency.path.as_posix()
        package.files = [
            {"file": dependency.path.name, "hash": "sha256:" + dependency.hash()}
        ]

        for extra in dependency.extras:
            if extra in package.extras:
                for dep in package.extras[extra]:
                    dep.activate()

                package.requires += package.extras[extra]

        return [package]

    @classmethod
    def get_package_from_file(cls, file_path):  # type: (Path) -> Package
        info = Inspector().inspect(file_path)
        if not info["name"]:
            raise RuntimeError(
                "Unable to determine the package name of {}".format(file_path)
            )

        package = Package(info["name"], info["version"])
        package.source_type = "file"
        package.source_url = file_path.as_posix()

        package.description = info["summary"]
        for req in info["requires_dist"]:
            dep = dependency_from_pep_508(req)
            for extra in dep.in_extras:
                if extra not in package.extras:
                    package.extras[extra] = []

                package.extras[extra].append(dep)

            if not dep.is_optional():
                package.requires.append(dep)

        if info["requires_python"]:
            package.python_versions = info["requires_python"]

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

        package.source_url = dependency.path.as_posix()
        package.develop = dependency.develop

        if dependency.base is not None:
            package.root_dir = dependency.base

        for extra in dependency.extras:
            if extra in package.extras:
                for dep in package.extras[extra]:
                    dep.activate()

                package.requires += package.extras[extra]

        return [package]

    @classmethod
    def get_package_from_directory(
        cls, directory, name=None
    ):  # type: (Path, Optional[str]) -> Package
        supports_poetry = False
        pyproject = directory.joinpath("pyproject.toml")
        if pyproject.exists():
            pyproject = TomlFile(pyproject)
            pyproject_content = pyproject.read()
            supports_poetry = (
                "tool" in pyproject_content and "poetry" in pyproject_content["tool"]
            )

        if supports_poetry:
            poetry = Factory().create_poetry(directory)

            pkg = poetry.package
            package = Package(pkg.name, pkg.version)

            for dep in pkg.requires:
                if not dep.is_optional():
                    package.requires.append(dep)

            for extra, deps in pkg.extras.items():
                if extra not in package.extras:
                    package.extras[extra] = []

                for dep in deps:
                    package.extras[extra].append(dep)

            package.python_versions = pkg.python_versions
        else:
            # Execute egg_info
            current_dir = os.getcwd()
            os.chdir(str(directory))

            try:
                cls._execute_setup()
            except EnvCommandError:
                result = SetupReader.read_from_directory(directory)
                if not result["name"]:
                    # The name could not be determined
                    # We use the dependency name
                    result["name"] = name

                if not result["version"]:
                    # The version could not be determined
                    # so we raise an error since it is mandatory
                    raise RuntimeError(
                        "Unable to retrieve the package version for {}".format(
                            directory
                        )
                    )

                package_name = result["name"]
                package_version = result["version"]
                python_requires = result["python_requires"]
                if python_requires is None:
                    python_requires = "*"

                package_summary = ""

                requires = ""
                for dep in result["install_requires"]:
                    requires += dep + "\n"

                if result["extras_require"]:
                    requires += "\n"

                for extra_name, deps in result["extras_require"].items():
                    requires += "[{}]\n".format(extra_name)

                    for dep in deps:
                        requires += dep + "\n"

                    requires += "\n"

                reqs = parse_requires(requires)
            else:
                os.chdir(current_dir)
                # Sometimes pathlib will fail on recursive
                # symbolic links, so we need to workaround it
                # and use the glob module instead.
                # Note that this does not happen with pathlib2
                # so it's safe to use it for Python < 3.4.
                if PY35:
                    egg_info = next(
                        Path(p)
                        for p in glob.glob(
                            os.path.join(str(directory), "**", "*.egg-info"),
                            recursive=True,
                        )
                    )
                else:
                    egg_info = next(directory.glob("**/*.egg-info"))

                meta = pkginfo.UnpackedSDist(str(egg_info))
                package_name = meta.name
                package_version = meta.version
                package_summary = meta.summary
                python_requires = meta.requires_python

                if meta.requires_dist:
                    reqs = list(meta.requires_dist)
                else:
                    reqs = []
                    requires = egg_info / "requires.txt"
                    if requires.exists():
                        with requires.open(encoding="utf-8") as f:
                            reqs = parse_requires(f.read())
            finally:
                os.chdir(current_dir)

            package = Package(package_name, package_version)
            package.description = package_summary

            for req in reqs:
                dep = dependency_from_pep_508(req)
                if dep.in_extras:
                    for extra in dep.in_extras:
                        if extra not in package.extras:
                            package.extras[extra] = []

                        package.extras[extra].append(dep)

                if not dep.is_optional():
                    package.requires.append(dep)

            if python_requires:
                package.python_versions = python_requires

        if name and name != package.name:
            # For now, the dependency's name must match the actual package's name
            raise RuntimeError(
                "The dependency name for {} does not match the actual package's name: {}".format(
                    name, package.name
                )
            )

        package.source_type = "directory"
        package.source_url = directory.as_posix()

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
            Inspector().download(url, temp_dir / file_name)

            package = cls.get_package_from_file(temp_dir / file_name)

        package.source_type = "url"
        package.source_url = url

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

            if not package.python_constraint.allows_all(
                self._package.python_constraint
            ):
                transitive_python_constraint = get_python_constraint_from_marker(
                    package.dependency.transitive_marker
                )
                intersection = package.python_constraint.intersect(
                    transitive_python_constraint
                )
                difference = transitive_python_constraint.difference(intersection)
                if (
                    transitive_python_constraint.is_any()
                    or self._package.python_constraint.intersect(
                        package.dependency.python_constraint
                    ).is_empty()
                    or intersection.is_empty()
                    or not difference.is_empty()
                ):
                    return [
                        Incompatibility(
                            [Term(package.to_dependency(), True)],
                            PythonCause(
                                package.python_versions, self._package.python_versions
                            ),
                        )
                    ]

        dependencies = [
            dep
            for dep in dependencies
            if dep.name not in self.UNSAFE_PACKAGES
            and self._package.python_constraint.allows_any(dep.python_constraint)
        ]

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
                    extras=package.requires_extras,
                    repository=package.dependency.source_name,
                ),
            )
            requires = package.requires
        else:
            requires = package.requires

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

        dependencies = [
            r
            for r in requires
            if self._package.python_constraint.allows_any(r.python_constraint)
        ]

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
            # tell the solver to enter compatibility mode
            # which means it will resolve for subsets
            # Python constraints
            #
            # For instance, if our root package requires Python ~2.7 || ^3.6
            # And we have one dependency that requires Python <3.6
            # and the other Python >=3.6 than the solver will solve
            # dependencies for Python >=2.7,<2.8 || >=3.4,<3.6
            # and Python >=3.6,<4.0
            python_constraints = []
            for constraint, _deps in by_constraint.items():
                python_constraints.append(_deps[0].python_versions)

            _deps = [str(_dep[0]) for _dep in by_constraint.values()]
            self.debug(
                "<warning>Different requirements found for {}.</warning>".format(
                    ", ".join(_deps[:-1]) + " and " + _deps[-1]
                )
            )
            raise CompatibilityError(*python_constraints)

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

            if (package.dependency.is_directory() or package.dependency.is_file()) and (
                dep.is_directory() or dep.is_file()
            ):
                relative_path = Path(
                    os.path.relpath(
                        dep.full_path.as_posix(), package.root_dir.as_posix()
                    )
                )

                # TODO: Improve the way we set the correct relative path for dependencies
                dep._path = relative_path

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
                    version = " (<b>{}</b>)".format(m2.group(2))
                else:
                    name = m.group(1)
                    version = ""

                message = (
                    "<fg=blue>fact</>: <c1>{}</c1>{} "
                    "depends on <c1>{}</c1> (<b>{}</b>)".format(
                        name, version, m.group(2), m.group(3)
                    )
                )
            elif " is " in message:
                message = re.sub(
                    "fact: (.+) is (.+)",
                    "<fg=blue>fact</>: <c1>\\1</c1> is <b>\\2</b>",
                    message,
                )
            else:
                message = re.sub(
                    r"(?<=: )(.+?) \((.+?)\)", "<c1>\\1</c1> (<b>\\2</b>)", message
                )
                message = "<fg=blue>fact</>: {}".format(message.split("fact: ")[1])
        elif message.startswith("selecting "):
            message = re.sub(
                r"selecting (.+?) \((.+?)\)",
                "<fg=blue>selecting</> <c1>\\1</c1> (<b>\\2</b>)",
                message,
            )
        elif message.startswith("derived:"):
            m = re.match(r"derived: (.+?) \((.+?)\)$", message)
            if m:
                message = "<fg=blue>derived</>: <c1>{}</c1> (<b>{}</b>)".format(
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
                    version = " (<b>{}</b>)".format(m2.group(2))
                else:
                    name = m.group(1)
                    version = ""

                message = (
                    "<fg=red;options=bold>conflict</>: <c1>{}</c1>{} "
                    "depends on <c1>{}</c1> (<b>{}</b>)".format(
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
                        "<comment>{}:</> {}".format(str(depth).rjust(4), s)
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
            indicator = Indicator(
                self._io, "{message} <fg=black;options=bold>({elapsed:2s})</>"
            )

            with indicator.auto(
                "<info>Resolving dependencies...</info>",
                "<info>Resolving dependencies...</info>",
            ):
                yield

        self._in_progress = False

    @classmethod
    def _execute_setup(cls):
        with temporary_directory() as tmp_dir:
            EnvManager.build_venv(tmp_dir)
            venv = VirtualEnv(Path(tmp_dir), Path(tmp_dir))
            venv.run("python", "setup.py", "egg_info")
