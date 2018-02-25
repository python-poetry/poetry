from typing import Any
from typing import Dict
from typing import List

from ..conflict import Conflict
from ..dependency_graph import DependencyGraph


class SpecificationProvider:
    """
    Provides information about specifcations and dependencies to the resolver,
    allowing the Resolver class to remain generic while still providing power
    and flexibility.

    This contract contains the methods
    that users of Molinillo must implement
    using knowledge of their own model classes.
    """
    
    @property
    def name_for_explicit_dependency_source(self) -> str:
        return 'user-specified dependency'
    
    @property
    def name_for_locking_dependency_source(self) -> str:
        return 'Lockfile'
    
    def search_for(self, dependency: Any) -> List[Any]:
        """
        Search for the specifications that match the given dependency.

        The specifications in the returned list will be considered in reverse
        order, so the latest version ought to be last.
        """
        return []

    def dependencies_for(self, specification: Any) -> List[Any]:
        """
        Returns the dependencies of specification.
        """
        return []

    def is_requirement_satisfied_by(self,
                                    requirement: Any,
                                    activated: DependencyGraph,
                                    spec: Any) -> bool:
        """
        Determines whether the given requirement is satisfied by the given
        spec, in the context of the current activated dependency graph.
        """
        return True

    def name_for(self, dependency: Any) -> str:
        """
        Returns the name for the given dependency.
        """
        return str(dependency)

    def sort_dependencies(self,
                          dependencies: List[Any],
                          activated: DependencyGraph,
                          conflicts: Dict[str, List[Conflict]]) -> List[Any]:
        """
        Sort dependencies so that the ones
        that are easiest to resolve are first.

        Easiest to resolve is (usually) defined by:
            1) Is this dependency already activated?
            2) How relaxed are the requirements?
            3) Are there any conflicts for this dependency?
            4) How many possibilities are there to satisfy this dependency?
        """
        return sorted(
            dependencies,
            key=lambda dep: (
                activated.vertex_named(self.name_for(dep)).payload is None,
                conflicts.get(self.name_for(dep) is None)
            )
        )

    def allow_missing(self, dependency) -> bool:
        """
        Returns whether this dependency, which has no possible matching
        specifications, can safely be ignored.
        """
        return False
