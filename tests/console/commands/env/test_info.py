from cleo.testers import CommandTester


def test_env_info_displays_complete_info(app):
    command = app.find("env:info")
    tester = CommandTester(command)

    tester.execute([("command", command.get_name())])

    expected = """
Virtualenv
==========

 * Python:         3.7.0
 * Implementation: CPython
 * Path:           /prefix
 * Valid:          True


System
======

 * Platform: darwin
 * OS:       posix
 * Python:   /base/prefix

"""

    assert tester.get_display(True) == expected


def test_env_info_displays_path_only(app):
    command = app.find("env:info")
    tester = CommandTester(command)

    tester.execute([("command", command.get_name()), ("--path", True)])

    expected = """/prefix"""

    assert tester.get_display(True) == expected
