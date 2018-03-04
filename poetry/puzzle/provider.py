import os
import shutil

from functools import cmp_to_key
from pathlib import Path
from tempfile import mkdtemp
from typing import Dict
from typing import List

from poetry.mixology import DependencyGraph
from poetry.mixology.conflict import Conflict
from poetry.mixology.contracts import SpecificationProvider

from poetry.packages import Dependency
from poetry.packages import Package
from poetry.packages import VCSDependency

from poetry.repositories import Pool

from poetry.semver import less_than

from poetry.utils.toml_file import TomlFile
from poetry.utils.venv import Venv

from poetry.vcs.git import Git


class Provider(SpecificationProvider):

    UNSAFE_PACKAGES = {'setuptools', 'distribute', 'pip'}

    def __init__(self, package: Package, pool: Pool):
        self._package = package
        self._pool = pool
        self._python_constraint = package.python_constraint

    @property
    def pool(self) -> Pool:
        return self._pool

    @property
    def name_for_explicit_dependency_source(self) -> str:
        return 'poetry.toml'

    @property
    def name_for_locking_dependency_source(self) -> str:
        return 'poetry.lock'

    def name_for(self, dependency: Dependency) -> str:
        """
        Returns the name for the given dependency.
        """
        return dependency.name

    def search_for(self, dependency: Dependency) -> List[Package]:
        """
        Search for the specifications that match the given dependency.

        The specifications in the returned list will be considered in reverse
        order, so the latest version ought to be last.
        """
        if dependency.is_vcs():
            return self.search_for_vcs(dependency)

        packages = self._pool.find_packages(
            dependency.name,
            dependency.constraint
        )

        packages.sort(
            key=cmp_to_key(
                lambda x, y:
                0 if x.version == y.version
                else -1 * int(less_than(x.version, y.version) or -1)
            )
        )

        return packages

    def search_for_vcs(self, dependency: VCSDependency) -> List[Package]:
        """
        Search for the specifications that match the given VCS dependency.

        Basically, we clone the repository in a temporary directory
        and get the information we need by checking out the specified reference.
        """
        if dependency.vcs != 'git':
            raise ValueError(f'Unsupported VCS dependency {dependency.vcs}')

        tmp_dir = Path(mkdtemp(prefix=f'pypoetry-git-{dependency.name}'))

        try:
            git = Git()
            git.clone(dependency.source, tmp_dir)
            git.checkout(dependency.reference, tmp_dir)
            revision = git.rev_parse(
                dependency.reference, tmp_dir
            ).strip()

            if dependency.tag or dependency.rev:
                revision = dependency.reference

            poetry = TomlFile(tmp_dir / 'poetry.toml')
            if poetry.exists():
                # If a poetry.toml file exists
                # We use it to get the information we need
                info = poetry.read()

                name = info['package']['name']
                version = info['package']['version']
                package = Package(name, version, version)
                for req_name, req_constraint in info['dependencies'].items():
                    package.add_dependency(req_name, req_constraint)
            else:
                # We need to use setup.py here
                # to figure the information we need
                # We need to place ourselves in the proper
                # folder for it to work
                current_dir = os.getcwd()
                os.chdir(tmp_dir.as_posix())

                try:
                    venv = Venv.create()
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

    def dependencies_for(self, package: Package):
        if package.source_type == 'git':
            # Information should already be set
            pass
        else:
            package = self._pool.package(package.name, package.version)

        return [
            r for r in package.requires
            if not r.is_optional()
            and r.name not in self.UNSAFE_PACKAGES
        ]

    def is_requirement_satisfied_by(self,
                                    requirement: Dependency,
                                    activated: DependencyGraph,
                                    package: Package) -> bool:
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

        return self._package.python_constraint.matches(package.python_constraint)

    def sort_dependencies(self,
                          dependencies: List[Dependency],
                          activated: DependencyGraph,
                          conflicts: Dict[str, List[Conflict]]):
        return sorted(dependencies, key=lambda d: [
            0 if activated.vertex_named(d.name).payload else 1,
            0 if d.allows_prereleases() else 1,
            0 if d.name in conflicts else 1,
            0 if activated.vertex_named(d.name).payload else len(self.search_for(d))
        ])
