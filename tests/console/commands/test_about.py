from cleo.testers import CommandTester


def test_about(app):
    command = app.find("about")
    tester = CommandTester(command)

    tester.execute()

    expected = """\
Poetry - Package Management for Python

Poetry is a dependency manager tracking local dependencies of your projects and libraries.
See https://github.com/sdispater/poetry for more information.
"""

    assert expected == tester.io.fetch_output()
