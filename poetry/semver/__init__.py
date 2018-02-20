from functools import cmp_to_key

from .comparison import less_than
from .constraints import Constraint
from .helpers import normalize_version
from .version_parser import VersionParser

SORT_ASC = 1
SORT_DESC = -1

_parser = VersionParser()


def statisfies(version, constraints):
    """
    Determine if given version satisfies given constraints.

    :type version: str
    :type constraints: str

    :rtype: bool
    """
    provider = Constraint('==', normalize_version(version))
    constraints = _parser.parse_constraints(constraints)

    return constraints.matches(provider)


def satisfied_by(versions, constraints):
    """
    Return all versions that satisfy given constraints.

    :type versions: List[str]
    :type constraints: str

    :rtype: List[str]
    """
    return [version for version in versions if statisfies(version, constraints)]


def sort(versions):
    return _sort(versions, SORT_ASC)


def rsort(versions):
    return _sort(versions, SORT_DESC)


def _sort(versions, direction):
    normalized = [
        (i, normalize_version(version))
        for i, version in enumerate(versions)
    ]
    normalized.sort(
        key=cmp_to_key(
            lambda x, y:
                0 if x[1] == y[1]
                else -direction * int(less_than(x[1], y[1]) or -1)
        )
    )

    return [versions[i] for i, _ in normalized]
