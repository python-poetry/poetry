"""
Constraint utilities

The focus of this module is any constraint support, but
PEP-0440 support trumps everything else.

With regard to SEM-VER compatibility, PEP-0440 is partially
but not fully compatible with all the SEM-VER specs; see

https://legacy.python.org/dev/peps/pep-0440/#semantic-versioning
> Semantic versions containing a hyphen (pre-releases - clause 10) or
> a plus sign (builds - clause 11) are not compatible with this PEP
> and are not permitted in the public version field.
"""

from typing import List

from poetry.semver import parse_single_constraint


def is_constraint(value):  # type: (str) -> bool
    """Check that a string is a single constraint

    :param value: any string
    :return: True if value is a constraint
    """
    try:
        return bool(parse_single_constraint(value))
    except (TypeError, ValueError):
        return False


def sorted_constraints(values, reverse=False):  # type: (List[str], bool) -> List[str]
    """Sort a list of single constraints (string);
    discards any string that is not a constraint.

    :param values: any strings
    :param reverse: sort descending (reverse=True) or ascending (reverse=False)
    :return: sorted values based on sort criteria for constraints
    """
    unsorted = (ver for ver in values if is_constraint(ver))
    return sorted(unsorted, key=parse_single_constraint, reverse=reverse)
