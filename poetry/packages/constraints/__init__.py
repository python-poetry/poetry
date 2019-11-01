import re

from .any_constraint import AnyConstraint
from .base_constraint import BaseConstraint
from .constraint import Constraint
from .union_constraint import UnionConstraint


BASIC_CONSTRAINT = re.compile(r"^(!?==?)?\s*([^\s]+?)\s*$")


def parse_constraint(constraints):
    if constraints == "*":
        return AnyConstraint()

    or_constraints = re.split(r"\s*\|\|?\s*", constraints.strip())
    or_groups = []
    for constraints in or_constraints:
        and_constraints = re.split(
            r"(?<!^)(?<![=>< ,]) *(?<!-)[, ](?!-) *(?!,|$)", constraints
        )
        constraint_objects = []

        if len(and_constraints) > 1:
            for constraint in and_constraints:
                constraint_objects.append(parse_single_constraint(constraint))
        else:
            constraint_objects.append(parse_single_constraint(and_constraints[0]))

        if len(constraint_objects) == 1:
            constraint = constraint_objects[0]
        else:
            constraint = constraint_objects[0]
            for next_constraint in constraint_objects[1:]:
                constraint = constraint.intersect(next_constraint)

        or_groups.append(constraint)

    if len(or_groups) == 1:
        return or_groups[0]
    else:
        return UnionConstraint(*or_groups)


def parse_single_constraint(constraint):  # type: (str) -> BaseConstraint
    # Basic comparator
    m = BASIC_CONSTRAINT.match(constraint)
    if m:
        op = m.group(1)
        if op is None:
            op = "=="

        version = m.group(2).strip()

        return Constraint(version, op)

    raise ValueError("Could not parse version constraint: {}".format(constraint))
