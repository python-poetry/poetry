from poetry.version.helpers import format_python_constraint
from poetry.semver.version_parser import VersionParser


def test_format_python_constraint():
    parser = VersionParser()
    constraint = parser.parse_constraints('~2.7 || ^3.6')

    result = format_python_constraint(constraint)

    assert result == '>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*'
