import pytest

from poetry.utils._compat import PY2
from poetry.utils._compat import Path


@pytest.fixture()
def tester(command_tester_factory):
    return command_tester_factory("check")


def test_check_valid(tester):
    tester.execute()

    expected = """\
All set!
"""

    assert expected == tester.io.fetch_output()


def test_check_invalid(mocker, tester):
    mocker.patch(
        "poetry.factory.Factory.locate",
        return_value=Path(__file__).parent.parent.parent
        / "fixtures"
        / "invalid_pyproject"
        / "pyproject.toml",
    )

    tester.execute()

    if PY2:
        expected = """\
Error: u'description' is a required property
Warning: A wildcard Python dependency is ambiguous. Consider specifying a more explicit one.
Warning: The "pendulum" dependency specifies the "allows-prereleases" property, which is deprecated. Use "allow-prereleases" instead.
"""
    else:
        expected = """\
Error: 'description' is a required property
Warning: A wildcard Python dependency is ambiguous. Consider specifying a more explicit one.
Warning: The "pendulum" dependency specifies the "allows-prereleases" property, which is deprecated. Use "allow-prereleases" instead.
"""

    assert expected == tester.io.fetch_output()
