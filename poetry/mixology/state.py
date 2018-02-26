from copy import copy

from .dependency_graph import DependencyGraph


class ResolutionState:

    def __init__(self, name, requirements, activated,
                 requirement, possibilities, depth,
                 conflicts, unused_unwind_options):
        self._name = name
        self._requirements = requirements
        self._activated = activated
        self._requirement = requirement
        self.possibilities = possibilities
        self._depth = depth
        self.conflicts = conflicts
        self.unused_unwind_options = unused_unwind_options

    @property
    def name(self):
        return self._name

    @property
    def requirements(self):
        return self._requirements

    @property
    def activated(self):
        return self._activated

    @property
    def requirement(self):
        return self._requirement

    @property
    def depth(self):
        return self._depth

    @classmethod
    def empty(cls):
        return cls(None, [], DependencyGraph(), None, None, 0, {}, [])

    def __repr__(self):
        return f'<{self.__class__.__name__} {self._name} ' \
               f'({str(self.requirement)})>'


class PossibilityState(ResolutionState):

    pass


class DependencyState(ResolutionState):

    def pop_possibility_state(self):
        state = PossibilityState(
            self._name,
            copy(self._requirements),
            self._activated,
            self._requirement,
            [self.possibilities.pop() if self.possibilities else None],
            self._depth + 1,
            copy(self.conflicts),
            copy(self.unused_unwind_options)
        )
        state.activated.tag(state)

        return state
