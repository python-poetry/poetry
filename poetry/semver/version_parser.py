import re

from typing import Tuple
from typing import Union

from .constraints.constraint import Constraint
from .constraints.base_constraint import BaseConstraint
from .constraints.empty_constraint import EmptyConstraint
from .constraints.multi_constraint import MultiConstraint
from .constraints.wildcard_constraint import WilcardConstraint
from .helpers import normalize_version, _expand_stability, parse_stability


class VersionParser:

    _modifier_regex = (
        '[._-]?'
        '(?:(stable|beta|b|RC|alpha|a|patch|post|pl|p)((?:[.-]?\d+)*)?)?'
        '([.-]?dev)?'
    )

    _stabilities = [
        'stable', 'RC', 'beta', 'alpha', 'dev'
    ]

    def parse_constraints(
            self, constraints
        ):  # type: (str) -> Union[Constraint, MultiConstraint]
        """
        Parses a constraint string into
        MultiConstraint and/or Constraint objects.
        """
        pretty_constraint = constraints

        m = re.match(
            '(?i)([^,\s]*?)@({})$'.format('|'.join(self._stabilities)),
            constraints
        )
        if m:
            constraints = m.group(1)
            if not constraints:
                constraints = '*'

        or_constraints = re.split('\s*\|\|?\s*', constraints.strip())
        or_groups = []
        for constraints in or_constraints:
            and_constraints = re.split(
                '(?<!^)(?<![=>< ,]) *(?<!-)[, ](?!-) *(?!,|$)',
                constraints
            )
            if len(and_constraints) > 1:
                constraint_objects = []
                for constraint in and_constraints:
                    for parsed_constraint in self._parse_constraint(constraint):
                        constraint_objects.append(parsed_constraint)
            else:
                constraint_objects = self._parse_constraint(and_constraints[0])

            if len(constraint_objects) == 1:
                constraint = constraint_objects[0]
            else:
                constraint = MultiConstraint(constraint_objects)

            or_groups.append(constraint)

        if len(or_groups) == 1:
            constraint = or_groups[0]
        elif len(or_groups) == 2:
            # parse the two OR groups and if they are contiguous we collapse
            # them into one constraint
            a = str(or_groups[0])
            b = str(or_groups[1])
            pos_a = a.find('<', 4)
            pos_b = a.find('<', 4)
            if (
                isinstance(or_groups[0], MultiConstraint)
                and isinstance(or_groups[1], MultiConstraint)
                and len(or_groups[0].constraints)
                and len(or_groups[1].constraints)
                and a[:3] == '>=' and pos_a != -1
                and b[:3] == '>=' and pos_b != -1
                and a[pos_a + 2:-1] == b[4:pos_b - 5]
            ):
                constraint = MultiConstraint(
                    Constraint('>=', a[4:pos_a - 5]),
                    Constraint('<', b[pos_b + 2:-1])
                )
            else:
                constraint = MultiConstraint(or_groups, False)
        else:
            constraint = MultiConstraint(or_groups, False)

        constraint.pretty_string = pretty_constraint

        return constraint

    def _parse_constraint(
            self, constraint
    ):  # type: (str) -> Union[Tuple[BaseConstraint], Tuple[BaseConstraint, BaseConstraint]]
        m = re.match('(?i)^v?[xX*](\.[xX*])*$', constraint)
        if m:
            return EmptyConstraint(),

        # Some versions have the form M.m.p-\d+
        # which means M.m.p-post\d+
        m = re.match(
            '(?i)^(~=?|\^|<> ?|!= ?|>=? ?|<=? ?|==? ?)v?(\d{{1,5}})(\.\d+)?(\.\d+)?(\.\d+)?-(\d+){}$'.format(
                self._modifier_regex
            ),
            constraint
        )
        if m:
            constraint = '{}{}{}{}{}'.format(
                m.group(1),
                m.group(2),
                m.group(3) if m.group(3) else '.0',
                m.group(4) if m.group(4) else '.0',
                m.group(5) if m.group(5) else '.0',
            )
            if m.group(6):
                constraint += '-post.' + m.group(6)

        version_regex = (
            'v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?{}(?:\+[^\s]+)?'
        ).format(self._modifier_regex)

        # Tilde range
        #
        # Like wildcard constraints, unsuffixed tilde constraints
        # say that they must be greater than the previous version,
        # to ensure that unstable instances of the current version are allowed.
        # However, if a stability suffix is added to the constraint,
        # then a >= match on the current version is used instead.
        m = re.match('(?i)^~=?{}$'.format(version_regex), constraint)
        if m:
            # Work out which position in the version we are operating at
            if m.group(4):
                position = 3
            elif m.group(3):
                position = 2
            elif m.group(2):
                position = 2
            else:
                position = 0

            # Calculate the stability suffix
            stability_suffix = ''
            if m.group(5):
                stability_suffix += '-{}{}'.format(
                    _expand_stability(m.group(5)),
                    '.' + m.group(6) if m.group(6) else ''
                )

            low_version = self._manipulate_version_string(
                m.groups(), position, 0
            ) + stability_suffix
            lower_bound = Constraint('>=', low_version)

            # For upper bound,
            # we increment the position of one more significance,
            # but high_position = 0 would be illegal
            high_position = max(0, position - 1)
            high_version = self._manipulate_version_string(
                m.groups(), high_position, 1
            )
            upper_bound = Constraint('<', high_version)

            return lower_bound, upper_bound

        # Caret range
        #
        # Allows changes that do not modify
        # the left-most non-zero digit in the [major, minor, patch] tuple.
        # In other words, this allows:
        #     - patch and minor updates for versions 1.0.0 and above,
        #     - patch updates for versions 0.X >=0.1.0,
        #     - and no updates for versions 0.0.X
        m = re.match('^\^{}($)'.format(version_regex), constraint)
        if m:
            if m.group(1) != '0' or not m.group(2):
                position = 0
            elif m.group(2) != '0' or not m.group(3):
                position = 1
            else:
                position = 2

            # Calculate the stability suffix
            stability_suffix = ''
            if m.group(5):
                stability_suffix += '-{}{}'.format(
                    _expand_stability(m.group(5)),
                    '.' + m.group(6) if m.group(6) else ''
                )

            low_version = normalize_version(constraint[1:])
            lower_bound = Constraint('>=', low_version)

            # For upper bound,
            # we increment the position of one more significance,
            # but high_position = 0 would be illegal
            high_version = self._manipulate_version_string(
                m.groups(), position, 1
            )
            upper_bound = Constraint('<', high_version)

            return lower_bound, upper_bound

        # X range
        #
        # Any of X, x, or * may be used to "stand in"
        # for one of the numeric values in the [major, minor, patch] tuple.
        # A partial version range is treated as an X-Range,
        # so the special character is in fact optional.
        m = re.match(
            '^(!= ?|==)?v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.[xX*])+$',
            constraint
        )
        if m:
            # We just leave it as is
            return WilcardConstraint(constraint),

        # Basic Comparators
        m = re.match('^(<>|!=|>=?|<=?|==?)?\s*(.*)', constraint)
        if m:
            try:
                version = normalize_version(m.group(2))
                stability = parse_stability(version)
                stability_re = re.match(
                    '(?:[^-]*)(-{})$'.format(self._modifier_regex),
                    m.group(2).lower()
                )
                if stability == 'stable' and stability_re:
                    version = version.split('-')[0] + stability_re.group(1)

                return Constraint(m.group(1) or '=', version),
            except ValueError:
                pass

        raise ValueError(
            'Could not parse version constraint: {}'.format(constraint)
        )

    def _manipulate_version_string(self, matches, position,
                                   increment=0, pad='0'):
        """
        Increment, decrement, or simply pad a version number.
        """
        matches = [matches[i]
                   if i <= len(matches) - 1 and matches[i] is not None else pad
                   for i in range(4)]
        for i in range(3, -1, -1):
            if i > position:
                matches[i] = pad
            elif i == position and increment:
                matches[i] = int(matches[i]) + increment
                # If matches[i] was 0, carry the decrement
                if matches[i] < 0:
                    matches[i] = pad
                    position -= 1

                    # Return null on a carry overflow
                    if i == 1:
                        return

        return '{}.{}.{}.{}'.format(matches[0], matches[1],
                                    matches[2], matches[3])
