from functools import cmp_to_key
from typing import Dict
from typing import List

from poetry.mixology import DependencyGraph
from poetry.mixology.conflict import Conflict
from poetry.mixology.contracts import SpecificationProvider

from poetry.packages import Dependency
from poetry.packages import Package

from poetry.repositories.repository import Repository

from poetry.semver import less_than
from poetry.semver.constraints import Constraint


class Provider(SpecificationProvider):

    UNSAFE_PACKAGES = {'setuptools', 'distribute', 'pip'}

    def __init__(self, repository: Repository):
        self._repository = repository

    @property
    def repository(self) -> Repository:
        return self._repository

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
        packages = self._repository.find_packages(
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

    def dependencies_for(self, package: Package):
        package = self._repository.package(package.name, package.version)

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

        if package.is_prerelease() and not requirement.accepts_prereleases():
            vertex = activated.vertex_named(package.name)

            if not any([r.accepts_prereleases() for r in vertex.requirements]):
                return False

        return requirement.constraint.matches(Constraint('==', package.version))

    def sort_dependencies(self,
                          dependencies: List[Dependency],
                          activated: DependencyGraph,
                          conflicts: Dict[str, List[Conflict]]):
        return sorted(dependencies, key=lambda d: [
            0 if activated.vertex_named(d.name).payload else 1,
            0 if d.accepts_prereleases() else 1,
            0 if d.name in conflicts else 1,
            0 if activated.vertex_named(d.name).payload else len(self.search_for(d))
        ])
