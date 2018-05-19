import os
import pkginfo
import shutil
import time

from cleo import ProgressIndicator
from contextlib import contextmanager
from functools import cmp_to_key
from tempfile import mkdtemp
from typing import List
from typing import Union

from poetry.packages import Dependency
from poetry.packages import DirectoryDependency
from poetry.packages import FileDependency
from poetry.packages import Package
from poetry.packages import VCSDependency
from poetry.packages import dependency_from_pep_508

from poetry.mixology.incompatibility import Incompatibility
from poetry.mixology.incompatibility_cause import DependencyCause
from poetry.mixology.incompatibility_cause import PlatformCause
from poetry.mixology.incompatibility_cause import PythonCause
from poetry.mixology.term import Term

from poetry.repositories import Pool

from poetry.utils._compat import Path
from poetry.utils.helpers import parse_requires
from poetry.utils.toml_file import TomlFile
from poetry.utils.venv import Venv

from poetry.vcs.git import Git

from .dependencies import Dependencies


class Indicator(ProgressIndicator):

    def __init__(self, output):
        super(Indicator, self).__init__(output)

        self.format = '%message% <fg=black;options=bold>(%elapsed:2s%)</>'

    @contextmanager
    def auto(self):
        message = '<info>Resolving dependencies</info>...'

        with super(Indicator, self).auto(message, message):
            yield

    def _formatter_elapsed(self):
        elapsed = time.time() - self.start_time

        return '{:.1f}s'.format(elapsed)


class Provider:

    UNSAFE_PACKAGES = {'setuptools', 'distribute', 'pip'}

    def __init__(self,
                 package,  # type: Package
                 pool,     # type: Pool
                 io
                 ):
        self._package = package
        self._pool = pool
        self._io = io
        self._python_constraint = package.python_constraint
        self._search_for = {}
        self._is_debugging = self._io.is_debug() or self._io.is_very_verbose()

    @property
    def pool(self):  # type: () -> Pool
        return self._pool

    @property
    def name_for_explicit_dependency_source(self):  # type: () -> str
        return 'pyproject.toml'

    @property
    def name_for_locking_dependency_source(self):  # type: () -> str
        return 'pyproject.lock'

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
            return [self._package]

        if dependency in self._search_for:
            return self._search_for[dependency]

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
                allow_prereleases=dependency.allows_prereleases()
            )

            packages.sort(
                key=cmp_to_key(
                    lambda x, y:
                    0 if x.version == y.version
                    else int(x.version < y.version or -1)
                )
            )

        self._search_for[dependency] = packages

        return self._search_for[dependency]

    def search_for_vcs(self, dependency):  # type: (VCSDependency) -> List[Package]
        """
        Search for the specifications that match the given VCS dependency.

        Basically, we clone the repository in a temporary directory
        and get the information we need by checking out the specified reference.
        """
        if dependency.vcs != 'git':
            raise ValueError(
                'Unsupported VCS dependency {}'.format(dependency.vcs)
            )

        tmp_dir = Path(
            mkdtemp(prefix='pypoetry-git-{}'.format(dependency.name))
        )

        try:
            git = Git()
            git.clone(dependency.source, tmp_dir)
            git.checkout(dependency.reference, tmp_dir)
            revision = git.rev_parse(
                dependency.reference, tmp_dir
            ).strip()

            if dependency.tag or dependency.rev:
                revision = dependency.reference

            pyproject = TomlFile(tmp_dir / 'pyproject.toml')
            pyproject_content = None
            has_poetry = False
            if pyproject.exists():
                pyproject_content = pyproject.read(True)
                has_poetry = (
                    'tool' in pyproject_content
                    and 'poetry' in pyproject_content['tool']
                )

            if pyproject_content and has_poetry:
                # If a pyproject.toml file exists
                # We use it to get the information we need
                info = pyproject_content['tool']['poetry']

                name = info['name']
                version = info['version']
                package = Package(name, version, version)
                package.source_type = dependency.vcs
                package.source_url = dependency.source
                package.source_reference = dependency.reference
                for req_name, req_constraint in info['dependencies'].items():
                    if req_name == 'python':
                        package.python_versions = req_constraint
                        continue

                    package.add_dependency(req_name, req_constraint)
            else:
                # We need to use setup.py here
                # to figure the information we need
                # We need to place ourselves in the proper
                # folder for it to work
                venv = Venv.create(self._io)

                current_dir = os.getcwd()
                os.chdir(tmp_dir.as_posix())

                try:
                    venv.run(
                        'python', 'setup.py', 'egg_info'
                    )

                    egg_info = list(tmp_dir.glob('*.egg-info'))[0]

                    meta = pkginfo.UnpackedSDist(str(egg_info))

                    if meta.requires_dist:
                        reqs = list(meta.requires_dist)
                    else:
                        reqs = []
                        requires = egg_info / 'requires.txt'
                        if requires.exists():
                            with requires.open() as f:
                                reqs = parse_requires(f.read())

                    package = Package(meta.name, meta.version)

                    for req in reqs:
                        package.requires.append(dependency_from_pep_508(req))
                except Exception:
                    raise
                finally:
                    os.chdir(current_dir)

            package.source_type = 'git'
            package.source_url = dependency.source
            package.source_reference = revision
        except Exception:
            raise
        finally:
            shutil.rmtree(tmp_dir.as_posix())

        return [package]

    def search_for_file(self, dependency
                        ):  # type: (FileDependency) -> List[Package]
        package = Package(dependency.name, dependency.pretty_constraint)
        package.source_type = 'file'
        package.source_reference = str(dependency.path)

        package.description = dependency.metadata.summary
        for req in dependency.metadata.requires_dist:
            package.requires.append(dependency_from_pep_508(req))

        if dependency.metadata.requires_python:
            package.python_versions = dependency.metadata.requires_python

        if dependency.metadata.platforms:
            package.platform = ' || '.join(dependency.metadata.platforms)

        package.hashes = [dependency.hash()]

        return [package]

    def search_for_directory(self, dependency
                             ):  # type: (DirectoryDependency) -> List[Package]
        package = dependency.package
        if dependency.extras:
            for extra in dependency.extras:
                if extra in package.extras:
                    for dep in package.extras[extra]:
                        dep.activate()

        return [package]

    def incompatibilities_for(self, package):  # type: (Package) -> List[Incompatibility]
        """
        Returns incompatibilities that encapsulate a given package's dependencies,
        or that it can't be safely selected.

        If multiple subsequent versions of this package have the same
        dependencies, this will return incompatibilities that reflect that. It
        won't return incompatibilities that have already been returned by a
        previous call to _incompatibilities_for().
        """
        # TODO: Check python versions
        if package.source_type in ['git', 'file', 'directory']:
            dependencies = package.requires
        elif package.is_root():
            dependencies = package.all_requires
        else:
            dependencies = self._dependencies_for(package)

        if not self._package.python_constraint.allows_any(package.python_constraint):
            return [
                Incompatibility(
                    [Term(package.to_dependency(), True)],
                    PythonCause(package.python_versions)
                )
            ]

        if not self._package.platform_constraint.matches(package.platform_constraint):
            return [
                Incompatibility(
                    [Term(package.to_dependency(), True)],
                    PlatformCause(package.platform)
                )
            ]

        return [
            Incompatibility([
                Term(package.to_dependency(), True),
                Term(dep, False)
            ], DependencyCause())
            for dep in dependencies
        ]

    def dependencies_for(self, package
                         ):  # type: (Package) -> Union[List[Dependency], Dependencies]
        if package.source_type in ['git', 'file', 'directory']:
            # Information should already be set
            return [
                r for r in package.requires
                if not r.is_optional()
                   and r.name not in self.UNSAFE_PACKAGES
            ]
        else:
            return Dependencies(package, self)

    def _dependencies_for(self, package):  # type: (Package) -> List[Dependency]
        complete_package = self._pool.package(
            package.name, package.version.text,
            extras=package.requires_extras
        )

        # Update package with new information
        package.requires = complete_package.requires
        package.description = complete_package.description
        package.python_versions = complete_package.python_versions
        package.platform = complete_package.platform
        package.hashes = complete_package.hashes

        return [
            r for r in package.requires
            if not r.is_optional()
            and self._package.python_constraint.allows_any(r.python_constraint)
            and self._package.platform_constraint.matches(package.platform_constraint)
            and r.name not in self.UNSAFE_PACKAGES
        ]

    # UI

    @property
    def output(self):
        return self._io

    def before_resolution(self):
        self._io.write('<info>Resolving dependencies</>')

        if self.is_debugging():
            self._io.new_line()

    def indicate_progress(self):
        if not self.is_debugging():
            self._io.write('.')

    def after_resolution(self):
        self._io.new_line()

    def debug(self, message, depth=0):
        if self.is_debugging():
            debug_info = str(message)
            debug_info = '\n'.join([
                '<comment>{}:</> {}'.format(str(depth).rjust(4), s)
                for s in debug_info.split('\n')
            ]) + '\n'

            self.output.write(debug_info)

    @contextmanager
    def progress(self):
        if not self._io.is_decorated() or self.is_debugging():
            self.output.writeln('Resolving dependencies...')
            yield
        else:
            indicator = Indicator(self._io)

            with indicator.auto():
                yield
