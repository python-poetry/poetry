from .constraints.constraint import Constraint


def greater_than(version1, version2):
    """
    Evaluates the expression: version1 > version2.

    :type version1: str
    :type version2: str

    :rtype: bool
    """
    return compare(version1, '>', version2)


def greater_than_or_equal(version1, version2):
    """
    Evaluates the expression: version1 >= version2.

    :type version1: str
    :type version2: str

    :rtype: bool
    """
    return compare(version1, '>=', version2)


def less_than(version1, version2):
    """
    Evaluates the expression: version1 < version2.

    :type version1: str
    :type version2: str

    :rtype: bool
    """
    return compare(version1, '<', version2)


def less_than_or_equal(version1, version2):
    """
    Evaluates the expression: version1 <= version2.

    :type version1: str
    :type version2: str

    :rtype: bool
    """
    return compare(version1, '<=', version2)


def equal(version1, version2):
    """
    Evaluates the expression: version1 == version2.

    :type version1: str
    :type version2: str

    :rtype: bool
    """
    return compare(version1, '==', version2)


def not_equal(version1, version2):
    """
    Evaluates the expression: version1 != version2.

    :type version1: str
    :type version2: str

    :rtype: bool
    """
    return compare(version1, '!=', version2)


def compare(version1, operator, version2):
    """
    Evaluates the expression: $version1 $operator $version2

    :type version1: str
    :type operator: str
    :type version2: str

    :rtype: bool
    """
    constraint = Constraint(operator, version2)

    return constraint.matches(Constraint('==', version1))
