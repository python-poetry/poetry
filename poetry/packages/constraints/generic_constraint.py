import operator
import re

from .base_constraint import BaseConstraint
from .empty_constraint import EmptyConstraint
from .multi_constraint import MultiConstraint


class GenericConstraint(BaseConstraint):
    """
    Represents a generic constraint.

    This is particularly useful for platform/system/os/extra constraints.
    """

    OP_EQ = operator.eq
    OP_NE = operator.ne

    _trans_op_str = {"=": OP_EQ, "==": OP_EQ, "!=": OP_NE}

    _trans_op_int = {OP_EQ: "==", OP_NE: "!="}

    def __init__(self, operator, version):
        if operator not in self._trans_op_str:
            raise ValueError(
                'Invalid operator "{}" given, '
                "expected one of: {}".format(
                    operator, ", ".join(self.supported_operators)
                )
            )

        self._operator = self._trans_op_str[operator]
        self._string_operator = self._trans_op_int[self._operator]
        self._version = version

    @property
    def supported_operators(self):
        return list(self._trans_op_str.keys())

    @property
    def operator(self):
        return self._operator

    @property
    def string_operator(self):
        return self._string_operator

    @property
    def version(self):
        return self._version

    def matches(self, provider):
        if not isinstance(provider, GenericConstraint):
            return provider.matches(self)

        is_equal_op = self.OP_EQ is self._operator
        is_non_equal_op = self.OP_NE is self._operator
        is_provider_equal_op = self.OP_EQ is provider.operator
        is_provider_non_equal_op = self.OP_NE is provider.operator

        if (
            is_equal_op
            and is_provider_equal_op
            or is_non_equal_op
            and is_provider_non_equal_op
        ):
            return self._version == provider.version

        if (
            is_equal_op
            and is_provider_non_equal_op
            or is_non_equal_op
            and is_provider_equal_op
        ):
            return self._version != provider.version

        return False

    @classmethod
    def parse(cls, constraints):
        """
        Parses a constraint string into
        MultiConstraint and/or PlatformConstraint objects.
        """
        pretty_constraint = constraints

        or_constraints = re.split("\s*\|\|?\s*", constraints.strip())
        or_groups = []
        for constraints in or_constraints:
            and_constraints = re.split(
                "(?<!^)(?<![ ,]) *(?<!-)[, ](?!-) *(?!,|$)", constraints
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
        m = re.match("(?i)^v?[xX*](\.[xX*])*$", constraint)
        if m:
            return (EmptyConstraint(),)

        # Basic Comparators
        m = re.match("^(!=|==?)?\s*(.*)", constraint)
        if m:
            return (GenericConstraint(m.group(1) or "=", m.group(2)),)

        raise ValueError("Could not parse generic constraint: {}".format(constraint))

    def __str__(self):
        op = self._trans_op_int[self._operator]
        if op == "==":
            op = ""
        else:
            op = op + " "

        return "{}{}".format(op, self._version)

    def __repr__(self):
        return "<GenericConstraint '{}'>".format(str(self))
