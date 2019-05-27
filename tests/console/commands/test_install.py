from cleo.testers import CommandTester

from tests.helpers import get_package


def test_install_all_extras(app_with_extras, repo, installer):
    command = app_with_extras.find("install")
    tester = CommandTester(command)

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cachy", "0.2.0"))

    tester.execute("--all-extras")

    expected = """\
Installing with all available extra dependencies.
Extras found: extras_a, extras_b

Updating dependencies
Resolving dependencies...

Writing lock file


Package operations: 2 installs, 0 updates, 0 removals

  - Installing cachy (0.2.0)
  - Installing pendulum (1.4.4)
  - Installing project-with-extras (1.2.3)
"""

    assert tester.io.fetch_output() == expected

    assert len(installer.installs) == 2

    content = app_with_extras.poetry.file.read()["tool"]["poetry"]

    assert "cachy" in content["dependencies"]
    assert content["dependencies"]["cachy"] == {"version": ">=0.2.0", "optional": True}

    assert "pendulum" in content["dependencies"]
    assert content["dependencies"]["pendulum"] == {
        "version": ">=1.4.4",
        "optional": True,
    }

    assert "extras_a" in content["extras"]
    assert content["extras"]["extras_a"] == ["pendulum"]

    assert "extras_b" in content["extras"]
    assert content["extras"]["extras_b"] == ["cachy"]
