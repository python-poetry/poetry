from cleo.testers import CommandTester

from poetry.utils._compat import PY2
from poetry.utils._compat import Path
from poetry.poetry import Poetry


def test_check_valid(app):
    command = app.find("check")
    tester = CommandTester(command)

    tester.execute([("command", command.get_name())])

    expected = """\
All set!
"""

    assert tester.get_display(True) == expected


def test_check_invalid(app):
    app._poetry = Poetry.create(
        Path(__file__).parent.parent.parent / "fixtures" / "invalid_pyproject"
    )
    command = app.find("check")
    tester = CommandTester(command)

    tester.execute([("command", command.get_name())])

    if PY2:
        expected = """\
Error: u'description' is a required property
Error: INVALID is not a valid license
Warning: A wildcard Python dependency is ambiguous. Consider specifying a more explicit one.
"""
    else:
        expected = """\
Error: 'description' is a required property
Error: INVALID is not a valid license
Warning: A wildcard Python dependency is ambiguous. Consider specifying a more explicit one.
"""

    assert tester.get_display(True) == expected
