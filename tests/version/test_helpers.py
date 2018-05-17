from poetry.version.helpers import format_python_constraint
from poetry.semver.semver import parse_constraint


def test_format_python_constraint():
    constraint = parse_constraint('~2.7 || ^3.6')

    result = format_python_constraint(constraint)

    assert result == '>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*'
