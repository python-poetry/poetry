from poetry.semver.constraints import MultiConstraint
from poetry.semver.version_parser import VersionParser


PYTHON_VERSION = [
    '2.7.*',
    '3.0.*', '3.1.*', '3.2.*', '3.3.*', '3.4.*',
    '3.5.*', '3.6.*', '3.7.*', '3.8.*',
]


def format_python_constraint(constraint):
    """
    This helper will help in transforming
    disjunctive constraint into proper constraint.
    """
    if not isinstance(constraint, MultiConstraint):
        return str(constraint)

    has_disjunctive = False
    for c in constraint.constraints:
        if isinstance(c, MultiConstraint) and c.is_disjunctive():
            has_disjunctive = True
            break

    parser = VersionParser()
    formatted = []
    accepted = []
    if not constraint.is_disjunctive() and not has_disjunctive:
        return str(constraint)

    for version in PYTHON_VERSION:
        matches = constraint.matches(parser.parse_constraints(version))
        if not matches:
            formatted.append('!=' + version)
        else:
            accepted.append(version)

    # Checking lower bound
    low = accepted[0]

    formatted.insert(0, '>=' + '.'.join(low.split('.')[:2]))

    return ', '.join(formatted)
