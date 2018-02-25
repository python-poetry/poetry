from collections import namedtuple


class UnwindDetails:

    def __init__(self,
                 state_index,
                 state_requirement,
                 requirement_tree,
                 conflicting_requirements,
                 requirement_trees,
                 requirements_unwound_to_instead):
        self.state_index = state_index
        self.state_requirement = state_requirement
        self.requirement_tree = requirement_tree
        self.conflicting_requirements = conflicting_requirements
        self.requirement_trees = requirement_trees
        self.requirements_unwound_to_instead = requirements_unwound_to_instead
        self._reversed_requirement_tree_index = None
        self._sub_dependencies_to_avoid = None
        self._all_requirements = None

    @property
    def reversed_requirement_tree_index(self):
        if self._reversed_requirement_tree_index is None:
            if self.state_requirement:
                self._reversed_requirement_tree_index = list(reversed(
                    self.requirement_tree
                )).index(self.state_requirement)
            else:
                self._reversed_requirement_tree_index = 999999

        return self._reversed_requirement_tree_index

    def unwinding_to_primary_requirement(self):
        return self.requirement_tree[-1] == self.state_requirement

    @property
    def sub_dependencies_to_avoid(self):
        if self._sub_dependencies_to_avoid is None:
            self._sub_dependencies_to_avoid = []
            for tree in self.requirement_trees:
                try:
                    index = tree.index(self.state_requirement)
                except ValueError:
                    continue

                if tree[index + 1] is not None:
                    self._sub_dependencies_to_avoid.append(tree[index + 1])

        return self._sub_dependencies_to_avoid
    
    @property
    def all_requirements(self):
        if self._all_requirements is None:
            self._all_requirements = [
                x
                for tree in self.requirement_trees
                for x in tree
            ]

        return self._all_requirements

    def __eq__(self, other):
        if not isinstance(other, UnwindDetails):
            return NotImplemented

        return (
            self.state_index == other.state_index
            and (
                self.reversed_requirement_tree_index
                == other.reversed_requirement_tree_index
            )
        )

    def __lt__(self, other):
        if not isinstance(other, UnwindDetails):
            return NotImplemented

        return self.state_index < other.state_index

    def __le__(self, other):
        if not isinstance(other, UnwindDetails):
            return NotImplemented

        return self.state_index <= other.state_index

    def __gt__(self, other):
        if not isinstance(other, UnwindDetails):
            return NotImplemented

        return self.state_index > other.state_index

    def __ge__(self, other):
        if not isinstance(other, UnwindDetails):
            return NotImplemented

        return self.state_index >= other.state_index

    def __hash__(self):
        return hash((id(self), self.state_index, self.state_requirement))
