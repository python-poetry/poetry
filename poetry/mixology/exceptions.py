from .helpers import flat_map


class ResolverError(Exception):

    pass


class NoSuchDependencyError(ResolverError):

    def __init__(self, dependency, required_by=None):
        if required_by is None:
            required_by = []

        sources = ' and '.join(['"{}"'.format(r) for r in required_by])
        message = 'Unable to find a specification for "{}"'.format(dependency)
        if sources:
            message += ' depended upon by {}'.format(sources)

        super().__init__(message)


class CircularDependencyError(ResolverError):

    def __init__(self, vertices):
        super(CircularDependencyError, self).__init__(
            'There is a circular dependency between {}'.format(
                ' and '.join([v.name for v in vertices])
            )
        )

        self._dependencies = [v.payload.possibilities[-1] for v in vertices]

    @property
    def dependencies(self):
        return self._dependencies


class VersionConflict(ResolverError):

    def __init__(self, conflicts, specification_provider):
        pairs = []

        for conflicting in flat_map(
            list(conflicts.values()), lambda x: x.requirements
        ):
            for source, conflict_requirements in conflicting.items():
                for c in conflict_requirements:
                    pairs.append((c, source))

        super().__init__(
            'Unable to satisfy the following requirements:\n\n'
            '{}'.format(
                '\n'.join('- "{}" required by "{}"'.format(r, d)
                          for r, d in pairs)
            )
        )

        self._conflicts = conflicts
        self._specification_provider = specification_provider

    @property
    def conflicts(self):
        return self._conflicts

    @property
    def specification_provider(self):
        return self._specification_provider

    def message_with_trees(self,
                           solver_name='Poetry',
                           possibility_type='possibility named',
                           reduce_trees=lambda trees: sorted(set(trees), key=str),
                           printable_requirement=str,
                           message_for_conflict=None,
                           version_for_spec=str):
        o = []
        for name, conflict in sorted(self._conflicts):
            o.append(
                '\n{} could not find compatible versions for {} "{}"_n'.format(
                    solver_name, possibility_type, name
                )
            )

            if conflict.locked_requirement:
                o.append(
                    ' In snapshot ({}):\n'.format(
                        self._specification_provider.name_for_locking_dependency_source
                    )
                )
                o.append(
                    '    {}\n'.format(
                        printable_requirement(conflict.locked_requirement)
                    )
                )
                o.append('\n')

            o.append(
                '  In {}:\n'.format(
                    self._specification_provider.name_for_explicit_dependency_source
                )
            )
            trees = reduce_trees(conflict.requirement_trees)
            ot = []
            for tree in trees:
                t = ''
                depth = 2
                for req in tree:
                    t += '  ' * depth + str(req)

                    if tree[-1] != req:
                        spec = conflict.activated_by_name.get(
                            self._specification_provider.name_for(req)
                        )
                        if spec:
                            t += ' was resolved to {}, which'.format(
                                version_for_spec(spec)
                            )

                        t += ' depends on'

                    t += '\n'
                    depth += 1

                ot.append(t)

            o.append('\n'.join(ot))

            if message_for_conflict:
                message_for_conflict(o, name, conflict)

        return ''.join(o).strip()


