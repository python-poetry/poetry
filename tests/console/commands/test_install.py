from cleo.testers import CommandTester

from tests.helpers import get_package


def test_install_target(app, repo, installer):
    command = app.find("install")
    tester = CommandTester(command)

    repo.add_package(get_package("simple-project", "1.2.3"))

    tester.execute("--target .")

    expected = """\
Updating dependencies
Resolving dependencies...

Writing lock file

Nothing to install or update

  - Installing simple-project (1.2.3)
"""

    assert expected == tester.io.fetch_output()
