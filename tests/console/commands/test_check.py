from cleo.testers import CommandTester


def test_about(app):
    command = app.find('check')
    tester = CommandTester(command)

    tester.execute([('command', command.get_name())])

    expected = """\
All set!
"""

    assert tester.get_display() == expected
