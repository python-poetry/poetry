import glob
import logging
import os
import pkginfo
import re
import time

from cleo import ProgressIndicator
from contextlib import contextmanager
from tempfile import mkdtemp
from typing import List

from poetry.packages import Dependency
from poetry.packages import DependencyPackage
from poetry.packages import DirectoryDependency
from poetry.packages import FileDependency
from poetry.packages import Package
from poetry.packages import PackageCollection
from poetry.packages import VCSDependency
from poetry.packages import dependency_from_pep_508

from poetry.mixology.incompatibility import Incompatibility
from poetry.mixology.incompatibility_cause import DependencyCause
from poetry.mixology.incompatibility_cause import PythonCause
from poetry.mixology.term import Term

from poetry.repositories import Pool

from poetry.utils._compat import PY35
from poetry.utils._compat import Path
from poetry.utils._compat import OrderedDict
from poetry.utils.helpers import parse_requires
from poetry.utils.helpers import safe_rmtree
from poetry.utils.env import Env
from poetry.utils.env import EnvCommandError
from poetry.utils.setup_reader import SetupReader

from poetry.version.markers import MarkerUnion
from poetry.vcs.git import Git

from .exceptions import CompatibilityError


logger = logging.getLogger(__name__)


class Indicator(ProgressIndicator):
    def __init__(self, output):
        super(Indicator, self).__init__(output)

        self.format = "%message% <fg=black;options=bold>(%elapsed:2s%)</>"

    @contextmanager
    def auto(self):
        message = "<info>Resolving dependencies</info>..."

        with super(Indicator, self).auto(message, message):
            yield

    def _formatter_elapsed(self):
        elapsed = time.time() - self.start_time

        return "{:.1f}s".format(elapsed)


class Provider:

    UNSAFE_PACKAGES = {"setuptools", "distribute", "pip"}

    def __init__(self, package, pool, io):  # type: (Package, Pool, ...) -> None
        self._package = package
        self._pool = pool
        self._io = io
        self._python_constraint = package.python_constraint
        self._search_for = {}
        self._is_debugging = self._io.is_debug() or self._io.is_very_verbose()
        self._in_progress = False

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
        else:
            constraint = dependency.constraint

            packages = self._pool.find_packages(
                dependency.name,
                constraint,
                extras=dependency.extras,
                allow_prereleases=dependency.allows_prereleases(),
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
        if dependency.vcs != "git":
            raise ValueError("Unsupported VCS dependency {}".format(dependency.vcs))

        tmp_dir = Path(mkdtemp(prefix="pypoetry-git-{}".format(dependency.name)))

        try:
            git = Git()
            git.clone(dependency.source, tmp_dir)
            git.checkout(dependency.reference, tmp_dir)
            revision = git.rev_parse(dependency.reference, tmp_dir).strip()

            if dependency.tag or dependency.rev:
                revision = dependency.reference

            directory_dependency = DirectoryDependency(
                dependency.name,
                tmp_dir,
                category=dependency.category,
                optional=dependency.is_optional(),
            )
            for extra in dependency.extras:
                directory_dependency.extras.append(extra)

            package = self.search_for_directory(directory_dependency)[0]

            package.source_type = "git"
            package.source_url = dependency.source
            package.source_reference = revision
        except Exception:
            raise
        finally:
            safe_rmtree(str(tmp_dir))

        return [package]

    def search_for_file(self, dependency):  # type: (FileDependency) -> List[Package]
        if dependency.path.suffix == ".whl":
            meta = pkginfo.Wheel(str(dependency.full_path))
        else:
            # Assume sdist
            meta = pkginfo.SDist(str(dependency.full_path))

        if dependency.name != meta.name:
            # For now, the dependency's name must match the actual package's name
            raise RuntimeError(
                "The dependency name for {} does not match the actual package's name: {}".format(
                    dependency.name, meta.name
                )
            )

        package = Package(meta.name, meta.version)
        package.source_type = "file"
        package.source_url = dependency.path.as_posix()

        package.description = meta.summary
        for req in meta.requires_dist:
            dep = dependency_from_pep_508(req)
            for extra in dep.in_extras:
                if extra not in package.extras:
                    package.extras[extra] = []

                package.extras[extra].append(dep)

            if not dep.is_optional():
                package.requires.append(dep)

        if meta.requires_python:
            package.python_versions = meta.requires_python

        package.hashes = [dependency.hash()]

        for extra in dependency.extras:
            if extra in package.extras:
                for dep in package.extras[extra]:
                    dep.activate()

                package.requires += package.extras[extra]

        return [package]

    def search_for_directory(
        self, dependency
    ):  # type: (DirectoryDependency) -> List[Package]
        if dependency.supports_poetry():
            from poetry.poetry import Poetry

            poetry = Poetry.create(dependency.full_path)

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
            os.chdir(str(dependency.full_path))

            try:
                cwd = dependency.full_path
                venv = Env.get(cwd)
                venv.run("python", "setup.py", "egg_info")
            except EnvCommandError:
                result = SetupReader.read_from_directory(dependency.full_path)
                if not result["name"]:
                    # The name could not be determined
                    # We use the dependency name
                    result["name"] = dependency.name

                if not result["version"]:
                    # The version could not be determined
                    # so we raise an error since it is mandatory
                    raise RuntimeError(
                        "Unable to retrieve the package version for {}".format(
                            dependency.path
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
                            os.path.join(str(dependency.full_path), "**", "*.egg-info"),
                            recursive=True,
                        )
                    )
                else:
                    egg_info = next(dependency.full_path.glob("**/*.egg-info"))

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
                        with requires.open() as f:
                            reqs = parse_requires(f.read())
            finally:
                os.chdir(current_dir)

            package = Package(package_name, package_version)

            if dependency.name != package.name:
                # For now, the dependency's name must match the actual package's name
                raise RuntimeError(
                    "The dependency name for {} does not match the actual package's name: {}".format(
                        dependency.name, package.name
                    )
                )

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

        package.source_type = "directory"
        package.source_url = dependency.path.as_posix()

        for extra in dependency.extras:
            if extra in package.extras:
                for dep in package.extras[extra]:
                    dep.activate()

                package.requires += package.extras[extra]

        return [package]

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
                intersection = package.python_constraint.intersect(
                    package.dependency.transitive_python_constraint
                )
                difference = package.dependency.transitive_python_constraint.difference(
                    intersection
                )
                if (
                    package.dependency.transitive_python_constraint.is_any()
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

        if not package.is_root() and package.source_type not in {
            "directory",
            "file",
            "git",
        }:
            package = DependencyPackage(
                package.dependency,
                self._pool.package(
                    package.name, package.version.text, extras=package.requires_extras
                ),
            )

        dependencies = [
            r
            for r in package.requires
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
                    if marker.is_empty():
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
        for dep in dependencies:
            if not package.dependency.python_constraint.is_any():
                dep.transitive_python_versions = str(
                    dep.python_constraint.intersect(
                        package.dependency.python_constraint
                    )
                )

            if (package.dependency.is_directory() or package.dependency.is_file()) and (
                dep.is_directory() or dep.is_file()
            ):
                if dep.path.as_posix().startswith(package.source_url):
                    relative = (Path(package.source_url) / dep.path).relative_to(
                        package.source_url
                    )
                else:
                    relative = Path(package.source_url) / dep.path

                # TODO: Improve the way we set the correct relative path for dependencies
                dep._path = relative

        package.requires = dependencies

        return package

    # UI

    @property
    def output(self):
        return self._io

    def debug(self, message, depth=0):
        if not (self.output.is_very_verbose() or self.output.is_debug()):
            return

        if message.startswith("fact:"):
            if "depends on" in message:
                m = re.match(r"fact: (.+?) depends on (.+?) \((.+?)\)", message)
                m2 = re.match(r"(.+?) \((.+?)\)", m.group(1))
                if m2:
                    name = m2.group(1)
                    version = " (<comment>{}</comment>)".format(m2.group(2))
                else:
                    name = m.group(1)
                    version = ""

                message = (
                    "<fg=blue>fact</>: <info>{}</info>{} "
                    "depends on <info>{}</info> (<comment>{}</comment>)".format(
                        name, version, m.group(2), m.group(3)
                    )
                )
            elif " is " in message:
                message = re.sub(
                    "fact: (.+) is (.+)",
                    "<fg=blue>fact</>: <info>\\1</info> is <comment>\\2</comment>",
                    message,
                )
            else:
                message = re.sub(
                    r"(?<=: )(.+?) \((.+?)\)",
                    "<info>\\1</info> (<comment>\\2</comment>)",
                    message,
                )
                message = "<fg=blue>fact</>: {}".format(message.split("fact: ")[1])
        elif message.startswith("selecting "):
            message = re.sub(
                r"selecting (.+?) \((.+?)\)",
                "<fg=blue>selecting</> <info>\\1</info> (<comment>\\2</comment>)",
                message,
            )
        elif message.startswith("derived:"):
            m = re.match(r"derived: (.+?) \((.+?)\)$", message)
            if m:
                message = "<fg=blue>derived</>: <info>{}</info> (<comment>{}</comment>)".format(
                    m.group(1), m.group(2)
                )
            else:
                message = "<fg=blue>derived</>: <info>{}</info>".format(
                    message.split("derived: ")[1]
                )
        elif message.startswith("conflict:"):
            m = re.match(r"conflict: (.+?) depends on (.+?) \((.+?)\)", message)
            if m:
                m2 = re.match(r"(.+?) \((.+?)\)", m.group(1))
                if m2:
                    name = m2.group(1)
                    version = " (<comment>{}</comment>)".format(m2.group(2))
                else:
                    name = m.group(1)
                    version = ""

                message = (
                    "<fg=red;options=bold>conflict</>: <info>{}</info>{} "
                    "depends on <info>{}</info> (<comment>{}</comment>)".format(
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

            self.output.write(debug_info)

    @contextmanager
    def progress(self):
        if not self._io.is_decorated() or self.is_debugging():
            self.output.writeln("Resolving dependencies...")
            yield
        else:
            indicator = Indicator(self._io)

            with indicator.auto():
                yield

        self._in_progress = False
