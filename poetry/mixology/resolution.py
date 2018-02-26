import logging

from copy import copy
from datetime import datetime

from typing import Any
from typing import List

from .contracts import SpecificationProvider
from .contracts import UI

from .exceptions import CircularDependencyError
from .exceptions import VersionConflict
from .conflict import Conflict
from .dependency_graph import DependencyGraph
from .helpers import flat_map
from .possibility_set import PossibilitySet
from .state import DependencyState
from .state import ResolutionState
from .unwind_details import UnwindDetails
from .utils import unique


logger = logging.getLogger(__name__)


class Resolution:

    def __init__(self,
                 provider: SpecificationProvider,
                 ui: UI,
                 requested: List[Any],
                 base: DependencyGraph):
        self._provider = provider
        self._ui = ui
        self._requested = requested
        self._original_requested = copy(requested)
        self._base = base
        self._states = []
        self._iteration_counter = 0
        self._progress_rate = 0.33
        self._iteration_rate = None
        self._parents_of = {}
        self._started_at = None

    @property
    def provider(self) -> SpecificationProvider:
        return self._provider
    
    @property
    def ui(self) -> UI:
        return self._ui

    @property
    def requested(self) -> List[Any]:
        return self._requested

    @property
    def base(self) -> DependencyGraph:
        return self._base

    @property
    def activated(self) -> DependencyGraph:
        return self.state.activated

    def resolve(self) -> DependencyGraph:
        """
        Resolve the original requested dependencies into a full
        dependency graph.
        """
        self._start()

        try:
            while self.state:
                if not self.state.requirement and not self.state.requirements:
                    break

                self._indicate_progress()
                if hasattr(self.state, 'pop_possibility_state'):
                    self._debug(
                        f'Creating possibility state for '
                        f'{str(self.state.requirement)} '
                        f'({len(self.state.possibilities)} remaining)'
                    )
                    s = self.state.pop_possibility_state()
                    if s:
                        self._states.append(s)
                        self.activated.tag(s)

                self._process_topmost_state()

            return self._resolve_activated_specs()
        finally:
            self._end()

    def _start(self) -> None:
        """
        Set up the resolution process.
        """
        self._started_at = datetime.now()

        self._debug(
            f'Starting resolution ({self._started_at})\n'
            f'Requested dependencies: '
            f'{[str(d) for d in self._original_requested]}'
        )
        self._ui.before_resolution()

        self._handle_missing_or_push_dependency_state(self._initial_state())

    def _resolve_activated_specs(self) -> DependencyGraph:
        for vertex in self.activated.vertices.values():
            if not vertex.payload:
                continue

            latest_version = None
            for possibility in reversed(list(vertex.payload.possibilities)):
                if all(
                    [
                        self._provider.is_requirement_satisfied_by(
                            req, self.activated, possibility
                        )
                        for req in vertex.requirements
                    ]
                ):
                    latest_version = possibility
                    break

            self.activated.set_payload(vertex.name, latest_version)

        return self.activated

    def _end(self) -> None:
        """
        Ends the resolution process
        """
        elapsed = (datetime.now() - self._started_at).total_seconds()

        self._ui.after_resolution()

        self._debug(
            f'Finished resolution ({self._iteration_counter} steps) '
            f'in {elapsed:.3f} seconds'
        )

    def _process_topmost_state(self) -> None:
        """
        Processes the topmost available RequirementState on the stack.
        """
        try:
            if self.possibility:
                self._attempt_to_activate()
            else:
                self._create_conflict()
                self._unwind_for_conflict()
        except CircularDependencyError as e:
            self._create_conflict(e)
            self._unwind_for_conflict()

    @property
    def possibility(self) -> PossibilitySet:
        """
        The current possibility that the resolution is trying.
        """
        if self.state.possibilities:
            return self.state.possibilities[-1]

    @property
    def state(self) -> DependencyState:
        """
        The current state the resolution is operating upon.
        """
        if self._states:
            return self._states[-1]

    @property
    def name(self) -> str:
        return self.state.name

    @property
    def requirement(self) -> Any:
        return self.state.requirement

    def _initial_state(self) -> DependencyState:
        """
        Create the initial state for the resolution, based upon the
        requested dependencies.
        """
        graph = DependencyGraph()
        for requested in self._original_requested:
            vertex = graph.add_vertex(
                self._provider.name_for(requested), None, True
            )
            vertex.explicit_requirements.append(requested)

        graph.tag('initial_state')

        requirements = self._provider.sort_dependencies(
            self._original_requested, graph, {}
        )
        initial_requirement = None
        if requirements:
            initial_requirement = requirements.pop(0)

        name = None
        if initial_requirement:
            name = self._provider.name_for(initial_requirement)

        return DependencyState(
            name,
            requirements,
            graph,
            initial_requirement,
            self._possibilities_for_requirement(initial_requirement, graph),
            0,
            {},
            []
        )

    def _unwind_for_conflict(self) -> None:
        """
        Unwinds the states stack because a conflict has been encountered
        """
        details_for_unwind = self._build_details_for_unwind()
        unwind_options = self.state.unused_unwind_options

        self._debug(
            'Unwinding for conflict: '
            '{} to {}'.format(
                str(self.state.requirement),
                details_for_unwind.state_index // 2
            ),
            self.state.depth
        )

        conflicts = self.state.conflicts
        sliced_states = self._states[details_for_unwind.state_index + 1:]
        self._states = self._states[:details_for_unwind.state_index + 1]

        self._raise_error_unless_state(conflicts)
        if sliced_states:
            self.activated.rewind_to(
                sliced_states[0] or 'initial_state'
            )

        self.state.conflicts = conflicts
        self.state.unused_unwind_options = unwind_options
        self._filter_possibilities_after_unwind(details_for_unwind)
        index = len(self._states) - 1
        for k, l in self._parents_of.items():
            self._parents_of[k] = [x for x in l if x < index]

        self.state.unused_unwind_options = [
            uw
            for uw in self.state.unused_unwind_options
            if uw.state_index < index
        ]

    def _raise_error_unless_state(self, conflicts) -> None:
        """
        Raise a VersionConflict error, or any underlying error,
        if there is no current state
        """
        if self.state:
            return

        errors = [c.underlying_error
                  for c in conflicts.values()
                  if c.underlying_error is not None]
        if errors:
            error = errors[0]
        else:
            error = VersionConflict(conflicts, self._provider)

        raise error

    def _build_details_for_unwind(self) -> UnwindDetails:
        """
        Return the details of the nearest index to which we could unwind.
        """
        # Get the possible unwinds for the current conflict
        current_conflict = self.state.conflicts[self.state.name]
        binding_requirements = self._binding_requirements_for_conflict(
            current_conflict
        )
        unwind_details = self._unwind_options_for_requirements(
            binding_requirements
        )

        last_detail_for_current_unwind = sorted(unwind_details)[-1]
        current_detail = last_detail_for_current_unwind

        # Look for past conflicts that could be unwound to affect the
        # requirement tree for the current conflict
        relevant_unused_unwinds = []
        for alternative in self.state.unused_unwind_options:
            intersecting_requirements = (
                set(last_detail_for_current_unwind.all_requirements)
                &
                set(alternative.requirements_unwound_to_instead)
            )
            if not intersecting_requirements:
                continue

            # Find the highest index unwind whilst looping through
            if alternative > current_detail:
                current_detail = alternative

            relevant_unused_unwinds.append(alternative)

        # Add the current unwind options to the `unused_unwind_options` array.
        # The "used" option will be filtered out during `unwind_for_conflict`.
        self.state.unused_unwind_options += [
            detail
            for detail in unwind_details
            if detail.state_index != -1
        ]

        # Update the requirements_unwound
        # to_instead on any relevant unused unwinds
        for d in relevant_unused_unwinds:
            d.requirements_unwound_to_instead.append(
                current_detail.state_requirement
            )
        for d in unwind_details:
            d.requirements_unwound_to_instead.append(
                current_detail.state_requirement
            )

        return current_detail

    def _unwind_options_for_requirements(self, binding_requirements):
        unwind_details = []
        trees = []

        for r in reversed(binding_requirements):
            partial_tree = [r]
            trees.append(partial_tree)
            unwind_details.append(
                UnwindDetails(
                    -1, None, partial_tree, binding_requirements, trees, []
                )
            )

            # If this requirement has alternative possibilities,
            # check if any would satisfy the other requirements
            # that created this conflict
            requirement_state = self._find_state_for(r)
            if self._conflict_fixing_possibilities(requirement_state,
                                                   binding_requirements):
                unwind_details.append(
                    UnwindDetails(
                        self._states.index(requirement_state),
                        r,
                        partial_tree,
                        binding_requirements,
                        trees,
                        []
                    )
                )

            # Next, look at the parent of this requirement,
            # and check if the requirement could have been avoided
            # if an alternative PossibilitySet had been chosen
            parent_r = self._parent_of(r)
            if parent_r is None:
                continue

            partial_tree.insert(0, parent_r)
            requirement_state = self._find_state_for(parent_r)
            possibilities = [
                r.name in map(lambda x: x.name, set_.dependencies)
                for set_ in requirement_state.possibilities
            ]
            if any(possibilities):
                unwind_details.append(
                    UnwindDetails(
                        self._states.index(requirement_state),
                        parent_r,
                        partial_tree,
                        binding_requirements,
                        trees,
                        []
                    )
                )

            # Finally, look at the grandparent and up of this requirement,
            # looking for any possibilities that wouldn't
            # create their parent requirement
            grandparent_r = self._parent_of(parent_r)
            while grandparent_r is not None:
                partial_tree.insert(0, grandparent_r)
                requirement_state = self._find_state_for(grandparent_r)
                possibilities = [
                    parent_r.name in map(lambda x: x.name, set_.dependencies)
                    for set_ in requirement_state.possibilities
                ]
                if any(possibilities):
                    unwind_details.append(
                        UnwindDetails(
                            self._states.index(requirement_state),
                            grandparent_r,
                            partial_tree,
                            binding_requirements,
                            trees,
                            []
                        )
                    )

                parent_r = grandparent_r
                grandparent_r = self._parent_of(parent_r)

        return unwind_details

    def _conflict_fixing_possibilities(self, state, binding_requirements):
        """
        Return whether or not the given state has any possibilities
        that could satisfy the given requirements

        :rtype: bool
        """
        if not state:
            return False

        return any([
            any([
                self._possibility_satisfies_requirements(
                    poss, binding_requirements
                )
            ])
            for possibility_set in state.possibilities
            for poss in possibility_set.possibilities
        ])

    def _filter_possibilities_after_unwind(self, unwind_details):
        """
        Filter a state's possibilities to remove any that would not fix the
        conflict we've just rewound from

        :type unwind_details: UnwindDetails
        """
        if not self.state or not self.state.possibilities:
            return

        if unwind_details.unwinding_to_primary_requirement():
            self._filter_possibilities_for_primary_unwind(unwind_details)
        else:
            self._filter_possibilities_for_parent_unwind(unwind_details)

    def _filter_possibilities_for_primary_unwind(self, unwind_details):
        """
        Filter a state's possibilities to remove any that would not satisfy
        the requirements in the conflict we've just rewound from.

        :type unwind_details: UnwindDetails
        """
        unwinds_to_state = [
            uw
            for uw in self.state.unused_unwind_options
            if uw.state_index == unwind_details.state_index
        ]
        unwinds_to_state.append(unwind_details)
        unwind_requirement_sets = [
            uw.conflicting_requirements
            for uw in unwinds_to_state
        ]

        possibilities = []
        for possibility_set in self.state.possibilities:
            if not any([
                any([
                    self._possibility_satisfies_requirements(
                        poss, requirements
                    )
                ])
                for poss in possibility_set.possibilities
                for requirements in unwind_requirement_sets
            ]):
                continue

            possibilities.append(possibility_set)

        self.state.possibilities = possibilities

    def _possibility_satisfies_requirements(self, possibility, requirements):
        name = self._provider.name_for(possibility)

        self.activated.tag('swap')
        if self.activated.vertex_named(name):
            self.activated.set_payload(name, possibility)

        satisfied = all([
            self._provider.is_requirement_satisfied_by(
                r, self.activated, possibility
            )
            for r in requirements
        ])
        self.activated.rewind_to('swap')

        return satisfied

    def _filter_possibilities_for_parent_unwind(self,
                                                unwind_details: UnwindDetails):
        """
        Filter a state's possibilities to remove any that would (eventually)
        the requirements in the conflict we've just rewound from.
        """
        unwinds_to_state = [
            uw
            for uw in self.state.unused_unwind_options
            if uw.state_index == unwind_details.state_index
        ]
        unwinds_to_state.append(unwind_details)

        primary_unwinds = unique([
            uw
            for uw in unwinds_to_state
            if uw.unwinding_to_primary_requirement()
        ])
        parent_unwinds = unique(unwinds_to_state)
        parent_unwinds = [uw for uw in parent_unwinds if uw not in primary_unwinds]

        allowed_possibility_sets = []
        for unwind in primary_unwinds:
            for possibility_set in self._states[unwind.state_index].possibilities:
                if any([
                    self._possibility_satisfies_requirements(
                        poss, unwind.conflicting_requirements
                    )
                    for poss in possibility_set.possibilities
                ]):
                    allowed_possibility_sets.append(possibility_set)

        requirements_to_avoid = list(flat_map(
            parent_unwinds,
            lambda x: x.sub_dependencies_to_avoid
        ))

        possibilities = []
        for possibility_set in self.state.possibilities:
            if (
                possibility_set in allowed_possibility_sets
                or [
                    r
                    for r in requirements_to_avoid
                    if r not in possibility_set.dependencies
                ]
            ):
                possibilities.append(possibility_set)

        self.state.possibilities = possibilities

    def _binding_requirements_for_conflict(self, conflict):
        """
        Return the minimal list of requirements that would cause the passed
        conflict to occur.

        :rtype: list
        """
        if conflict.possibility is None:
            return [conflict.requirement]

        possible_binding_requirements_set = list(conflict.requirements.values())
        possible_binding_requirements = []
        for reqs in possible_binding_requirements_set:
            if isinstance(reqs, list):
                possible_binding_requirements += reqs
            else:
                possible_binding_requirements.append(reqs)

        possible_binding_requirements = unique(possible_binding_requirements)

        # When there’s a `CircularDependency` error the conflicting requirement
        # (the one causing the circular) won’t be `conflict.requirement`
        # (which won’t be for the right state, because we won’t have created it,
        # because it’s circular).
        # We need to make sure we have that requirement in the conflict’s list,
        # otherwise we won’t be able to unwind properly, so we just return all
        # the requirements for the conflict.
        if conflict.underlying_error:
            return possible_binding_requirements

        possibilities = self._provider.search_for(conflict.requirement)

        # If all the requirements together don't filter out all possibilities,
        # then the only two requirements we need to consider are the initial one
        # (where the dependency's version was first chosen) and the last
        if self._binding_requirement_in_set(
            None, possible_binding_requirements,
            possibilities
        ):
            return list(filter(None, [
                conflict.requirement,
                self._requirement_for_existing_name(
                    self._provider.name_for(conflict.requirement)
                )
            ]))

        # Loop through the possible binding requirements, removing each one
        # that doesn't bind. Use a reversed as we want the earliest set of
        # binding requirements.
        binding_requirements = copy(possible_binding_requirements)
        for req in reversed(possible_binding_requirements):
            if req == conflict.requirement:
                continue

            if not self._binding_requirement_in_set(
                req, binding_requirements, possibilities
            ):
                index = binding_requirements.index(req)
                del binding_requirements[index]

        return binding_requirements

    def _binding_requirement_in_set(self,
                                    requirement,
                                    possible_binding_requirements,
                                    possibilities) -> bool:
        """
        Return whether or not the given requirement is required
        to filter out all elements of the list of possibilities.
        """
        return any([
            self._possibility_satisfies_requirements(
                poss,
                set(possible_binding_requirements) - set([requirement])
            )
            for poss in possibilities
        ])

    def _parent_of(self, requirement):
        if not requirement:
            return

        if requirement not in self._parents_of:
            self._parents_of[requirement] = []

        if not self._parents_of[requirement]:
            return

        try:
            index = self._parents_of[requirement][-1]
        except ValueError:
            return

        try:
            parent_state = self._states[index]
        except ValueError:
            return

        return parent_state.requirement

    def _requirement_for_existing_name(self, name):
        vertex = self.activated.vertex_named(name)
        if not vertex:
            return

        if not vertex.payload:
            return

        for s in self._states:
            if s.name == name:
                return s.requirement

    def _find_state_for(self, requirement):
        if not requirement:
            return

        for s in self._states:
            if s.requirement == requirement:
                return s

    def _create_conflict(self, underlying_error=None):
        vertex = self.activated.vertex_named(self.state.name)
        locked_requirement = self._locked_requirement_named(self.state.name)

        requirements = {}
        if vertex.explicit_requirements:
            requirements[self._provider.name_for_explicit_dependency_source] = vertex.explicit_requirements

        if locked_requirement:
            requirements[self._provider.name_for_locking_dependency_source] = [locked_requirement]

        for edge in vertex.incoming_edges:
            if edge.origin.payload.latest_version not in requirements:
                requirements[edge.origin.payload.latest_version] = []

            requirements[edge.origin.payload.latest_version].insert(0, edge.requirement)

        activated_by_name = {}
        for v in self.activated:
            if v.payload:
                activated_by_name[v.name] = v.payload.latest_version

        conflict = Conflict(
            self.requirement,
            requirements,
            vertex.payload.latest_version if vertex.payload else None,
            self.possibility,
            locked_requirement,
            self.requirement_trees,
            activated_by_name,
            underlying_error
        )

        self.state.conflicts[self.name] = conflict

        return conflict
        
    @property
    def requirement_trees(self):
        vertex = self.activated.vertex_named(self.state.name)
        return [self._requirement_tree_for(r) for r in vertex.requirements]

    def _requirement_tree_for(self, requirement):
        tree = []
        while requirement:
            tree.insert(0, requirement)
            requirement = self._parent_of(requirement)

        return tree

    def _indicate_progress(self):
        self._iteration_counter += 1
        progress_rate = self._ui.progress_rate or self._progress_rate
        if self._iteration_rate is None:
            if (datetime.now() - self._started_at).total_seconds() >= progress_rate:
                self._iteration_rate = self._iteration_counter

        if self._iteration_rate and (self._iteration_counter % self._iteration_rate) == 0:
            self._ui.indicate_progress()

    def _debug(self, message, depth=0):
        self._ui.debug(message, depth)

    def _attempt_to_activate(self):
        self._debug(
            f'Attempting to activate {str(self.possibility)}',
            self.state.depth,
        )
        existing_vertex = self.activated.vertex_named(self.state.name)
        if existing_vertex.payload:
            self._debug(
                'Found existing spec ({})'.format(existing_vertex.payload),
                self.state.depth
            )
            self._attempt_to_filter_existing_spec(existing_vertex)
        else:
            latest = self.possibility.latest_version
            possibilities = []
            for possibility in self.possibility.possibilities:
                if self._provider.is_requirement_satisfied_by(
                    self.requirement, self.activated, possibility
                ):
                    possibilities.append(possibility)

            self.possibility.possibilities = possibilities

            if self.possibility.latest_version is None:
                # ensure there's a possibility for better error messages
                if latest:
                    self.possibility.possibilities.append(latest)

                self._create_conflict()
                self._unwind_for_conflict()
            else:
                self._activate_new_spec()

    def _attempt_to_filter_existing_spec(self, vertex):
        """
        Attempt to update the existing vertex's
        `PossibilitySet` with a filtered version.
        """
        filtered_set = self._filtered_possibility_set(vertex)
        if filtered_set.possibilities:
            self.activated.set_payload(self.name, filtered_set)
            new_requirements = copy(self.state.requirements)
            self._push_state_for_requirements(new_requirements, False)
        else:
            self._create_conflict()
            self._debug(
                f'Unsatisfied by existing spec ({str(vertex.payload)})',
                self.state.depth
            )
            self._unwind_for_conflict()

    def _filtered_possibility_set(self, vertex):
        possibilities = [
            p
            for p in vertex.payload.possibilities
            if p in self.possibility.possibilities
        ]
        return PossibilitySet(
            vertex.payload.dependencies,
            possibilities
        )

    def _locked_requirement_named(self, requirement_name):
        vertex = self.base.vertex_named(requirement_name)

        if vertex:
            return vertex.payload

    def _activate_new_spec(self):
        if self.state.name in self.state.conflicts:
            del self.state.conflicts[self.name]

        self._debug(
            f'Activated {self.state.name} at {str(self.possibility)}',
            self.state.depth
        )
        self.activated.set_payload(self.state.name, self.possibility)
        self._require_nested_dependencies_for(self.possibility)

    def _require_nested_dependencies_for(self, possibility_set):
        nested_dependencies = self._provider.dependencies_for(
            possibility_set.latest_version
        )
        self._debug(
            f'Requiring nested dependencies '
            f'({", ".join([str(d) for d in nested_dependencies])})',
            self.state.depth
        )

        for d in nested_dependencies:
            self.activated.add_child_vertex(
                self._provider.name_for(d),
                None,
                [self._provider.name_for(possibility_set.latest_version)],
                d
            )
            parent_index = len(self._states) - 1

            if d not in self._parents_of:
                self._parents_of[d] = []

            parents = self._parents_of[d]
            if not parents:
                parents.append(parent_index)

        self._push_state_for_requirements(
            self.state.requirements + nested_dependencies,
            len(nested_dependencies) > 0
        )

    def _push_state_for_requirements(self,
                                     new_requirements,
                                     requires_sort=True,
                                     new_activated=None):
        if new_activated is None:
            new_activated = self.activated

        if requires_sort:
            new_requirements = self._provider.sort_dependencies(
                unique(new_requirements), new_activated, self.state.conflicts
            )

        while True:
            new_requirement = None
            if new_requirements:
                new_requirement = new_requirements.pop(0)

            if (
                new_requirement is None
                    or not any([
                        s.requirement == new_requirement
                        for s in self._states
                    ])
            ):
                break

        new_name = ''
        if new_requirement:
            new_name = self._provider.name_for(new_requirement)

        possibilities = self._possibilities_for_requirement(new_requirement)

        self._handle_missing_or_push_dependency_state(
            DependencyState(
                new_name, new_requirements, new_activated,
                new_requirement, possibilities, self.state.depth,
                copy(self.state.conflicts),
                copy(self.state.unused_unwind_options)
            )
        )

    def _possibilities_for_requirement(self, requirement, activated=None):
        if activated is None:
            activated = self.activated

        if not requirement:
            return []

        if self._locked_requirement_named(self._provider.name_for(requirement)):
            return self._locked_requirement_possibility_set(
                requirement, activated
            )

        return self._group_possibilities(
            self._provider.search_for(requirement)
        )

    def _locked_requirement_possibility_set(self, requirement, activated=None):
        if activated is None:
            activated = self.activated

        all_possibilities = self._provider.search_for(requirement)
        locked_requirement = self._locked_requirement_named(
            self._provider.name_for(requirement)
        )

        # Longwinded way to build a possibilities list with either the locked
        # requirement or nothing in it. Required, since the API for
        # locked_requirement isn't guaranteed.
        locked_possibilities = [
            possibility
            for possibility in all_possibilities
            if self._provider.is_requirement_satisfied_by(
                locked_requirement, activated, possibility
            )
        ]

        return self._group_possibilities(locked_possibilities)

    def _group_possibilities(self, possibilities):
        possibility_sets = []
        current_possibility_set = None

        for possibility in reversed(possibilities):
            dependencies = self._provider.dependencies_for(possibility)
            if current_possibility_set and current_possibility_set.dependencies == dependencies:
                current_possibility_set.possibilities.insert(0, possibility)
            else:
                possibility_sets.insert(
                    0, PossibilitySet(dependencies, [possibility])
                )
                current_possibility_set = possibility_sets[0]

        return possibility_sets

    def _handle_missing_or_push_dependency_state(self, state):
        if (
            state.requirement
            and not state.possibilities
            and self._provider.allow_missing(state.requirement)
        ):
            state.activated.detach_vertex_named(state.name)
            self._push_state_for_requirements(
                copy(state.requirements), False, state.activated
            )
        else:
            self._states.append(state)
            state.activated.tag(state)
