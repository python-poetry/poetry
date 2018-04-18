import os
import shutil

from functools import cmp_to_key
from tempfile import mkdtemp
from typing import Dict
from typing import List

from poetry.mixology import DependencyGraph
from poetry.mixology.conflict import Conflict
from poetry.mixology.contracts import SpecificationProvider

from poetry.packages import Dependency
from poetry.packages import FileDependency
from poetry.packages import Package
from poetry.packages import VCSDependency
from poetry.packages import dependency_from_pep_508

from poetry.repositories import Pool

from poetry.semver import less_than

from poetry.utils._compat import Path
from poetry.utils.toml_file import TomlFile
from poetry.utils.venv import Venv

from poetry.vcs.git import Git


class Provider(SpecificationProvider):

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
        self._base_dg = DependencyGraph()
        self._search_for = {}

    @property
    def pool(self):  # type: () -> Pool
        return self._pool

    @property
    def name_for_explicit_dependency_source(self):  # type: () -> str
        return 'pyproject.toml'

    @property
    def name_for_locking_dependency_source(self):  # type: () -> str
        return 'pyproject.lock'

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
        if dependency in self._search_for:
            return self._search_for[dependency]

        if dependency.is_vcs():
            packages = self.search_for_vcs(dependency)
        elif dependency.is_file():
            packages = self.search_for_file(dependency)
        else:
            packages = self._pool.find_packages(
                dependency.name,
                dependency.constraint,
                extras=dependency.extras,
            )

            packages.sort(
                key=cmp_to_key(
                    lambda x, y:
                    0 if x.version == y.version
                    else -1 * int(less_than(x.version, y.version) or -1)
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
                current_dir = os.getcwd()
                os.chdir(tmp_dir.as_posix())

                try:
                    venv = Venv.create(self._io)
                    output = venv.run(
                        'python', 'setup.py',
                        '--name', '--version'
                    )
                    output = output.split('\n')
                    name = output[-3]
                    version = output[-2]
                    package = Package(name, version, version)
                    # Figure out a way to get requirements
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

    def dependencies_for(self, package):  # type: (Package) -> List[Dependency]
        if package.source_type in ['git', 'file']:
            # Information should already be set
            pass
        else:
            complete_package = self._pool.package(package.name, package.version)

            # Update package with new information
            package.requires = complete_package.requires
            package.description = complete_package.description
            package.python_versions = complete_package.python_versions
            package.platform = complete_package.platform
            package.hashes = complete_package.hashes

        return [
            r for r in package.requires
            if not r.is_optional()
            and r.name not in self.UNSAFE_PACKAGES
        ]

    def is_requirement_satisfied_by(self,
                                    requirement,  # type: Dependency
                                    activated,    # type: DependencyGraph
                                    package       # type: Package
                                    ):  # type: (...) -> bool
        """
        Determines whether the given requirement is satisfied by the given
        spec, in the context of the current activated dependency graph.
        """
        if isinstance(requirement, Package):
            return requirement == package

        if not requirement.accepts(package):
            return False

        if package.is_prerelease() and not requirement.allows_prereleases():
            vertex = activated.vertex_named(package.name)

            if not any([r.allows_prereleases() for r in vertex.requirements]):
                return False

        return (
            self._package.python_constraint.matches(package.python_constraint)
            and self._package.platform_constraint.matches(package.platform_constraint)
        )

    def sort_dependencies(self,
                          dependencies,  # type: List[Dependency]
                          activated,     # type: DependencyGraph
                          conflicts      # type: Dict[str, List[Conflict]]
                          ):  # type: (...) -> List[Dependency]
        return sorted(dependencies, key=lambda d: [
            0 if activated.vertex_named(d.name).payload else 1,
            0 if activated.vertex_named(d.name).root else 1,
            0 if d.allows_prereleases() else 1,
            0 if d.name in conflicts else 1
        ])
