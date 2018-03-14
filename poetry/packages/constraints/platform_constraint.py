import operator
import re

from poetry.semver.constraints import EmptyConstraint
from poetry.semver.constraints import MultiConstraint
from poetry.semver.constraints.base_constraint import BaseConstraint


class PlatformConstraint(BaseConstraint):

    OP_EQ = operator.eq
    OP_NE = operator.ne

    _trans_op_str = {
        '=': OP_EQ,
        '==': OP_EQ,
        '!=': OP_NE
    }

    _trans_op_int = {
        OP_EQ: '==',
        OP_NE: '!='
    }

    def __init__(self, operator, platform):
        if operator not in self._trans_op_str:
            raise ValueError(
                f'Invalid operator "{operator}" given, '
                f'expected one of: {", ".join(self.supported_operators)}'
            )

        self._operator = self._trans_op_str[operator]
        self._string_operator = operator
        self._platform = platform

    @property
    def supported_operators(self) -> list:
        return list(self._trans_op_str.keys())

    @property
    def operator(self):
        return self._operator

    @property
    def string_operator(self):
        return self._string_operator

    @property
    def platform(self) -> str:
        return self._platform

    def matches(self, provider):
        if not isinstance(provider, (PlatformConstraint, EmptyConstraint)):
            raise ValueError(
                'Platform constraints can only be compared with each other'
            )

        if isinstance(provider, EmptyConstraint):
            return True

        is_equal_op = self.OP_EQ is self._operator
        is_non_equal_op = self.OP_NE is self._operator
        is_provider_equal_op = self.OP_EQ is provider.operator
        is_provider_non_equal_op = self.OP_NE is provider.operator

        if (
            is_equal_op and is_provider_equal_op
            or is_non_equal_op and is_provider_non_equal_op
        ):
            return self._platform == provider.platform

        if (
            is_equal_op and is_provider_non_equal_op
            or is_non_equal_op and is_provider_equal_op
        ):
            return self._platform != provider.platform

        return False

    @classmethod
    def parse(cls, constraints):
        """
        Parses a constraint string into
        MultiConstraint and/or PlatformConstraint objects.
        """
        pretty_constraint = constraints

        or_constraints = re.split('\s*\|\|?\s*', constraints.strip())
        or_groups = []
        for constraints in or_constraints:
            and_constraints = re.split(
                '(?<!^)(?<![ ,]) *(?<!-)[, ](?!-) *(?!,|$)',
                constraints
            )
            if len(and_constraints) > 1:
                constraint_objects = []
                for constraint in and_constraints:
                    for parsed_constraint in cls._parse_constraint(constraint):
                        constraint_objects.append(parsed_constraint)
            else:
                constraint_objects = cls._parse_constraint(and_constraints[0])

            if len(constraint_objects) == 1:
                constraint = constraint_objects[0]
            else:
                constraint = MultiConstraint(constraint_objects)

            or_groups.append(constraint)

        if len(or_groups) == 1:
            constraint = or_groups[0]
        else:
            constraint = MultiConstraint(or_groups, False)

        constraint.pretty_string = pretty_constraint

        return constraint

    @classmethod
    def _parse_constraint(cls, constraint):
        m = re.match('(?i)^v?[xX*](\.[xX*])*$', constraint)
        if m:
            return EmptyConstraint(),

        # Basic Comparators
        m = re.match('^(!=|==?)?\s*(.*)', constraint)
        if m:
            return PlatformConstraint(m.group(1) or '=', m.group(2)),

        raise ValueError(
            'Could not parse platform constraint: {}'.format(constraint)
        )

    def __str__(self):
        op = self._trans_op_int[self._operator]
        if op == '==':
            op = ''
        else:
            op = op + ' '

        return '{}{}'.format(
            op,
            self._platform
        )

    def __repr__(self):
        return '<PlatformConstraint \'{}\'>'.format(str(self))
