import pytest

from poetry.console.commands.version import VersionCommand


@pytest.fixture()
def command():
    return VersionCommand()


@pytest.fixture
def tester(command_tester_factory):
    return command_tester_factory("version")


@pytest.mark.parametrize(
    "version, rule, expected",
    [
        ("0.0.0", "patch", "0.0.1"),
        ("0.0.0", "minor", "0.1.0"),
        ("0.0.0", "major", "1.0.0"),
        ("0.0", "major", "1.0"),
        ("0.0", "minor", "0.1"),
        ("0.0", "patch", "0.0.1"),
        ("1.2.3", "patch", "1.2.4"),
        ("1.2.3", "minor", "1.3.0"),
        ("1.2.3", "major", "2.0.0"),
        ("1.2.3", "prepatch", "1.2.4-alpha.0"),
        ("1.2.3", "preminor", "1.3.0-alpha.0"),
        ("1.2.3", "premajor", "2.0.0-alpha.0"),
        ("1.2.3-beta.1", "patch", "1.2.3"),
        ("1.2.3-beta.1", "minor", "1.3.0"),
        ("1.2.3-beta.1", "major", "2.0.0"),
        ("1.2.3-beta.1", "prerelease", "1.2.3-beta.2"),
        ("1.2.3-beta1", "prerelease", "1.2.3-beta.2"),
        ("1.2.3beta1", "prerelease", "1.2.3-beta.2"),
        ("1.2.3b1", "prerelease", "1.2.3-beta.2"),
        ("1.2.3", "prerelease", "1.2.4-alpha.0"),
        ("0.0.0", "1.2.3", "1.2.3"),
    ],
)
def test_increment_version(version, rule, expected, command):
    assert expected == command.increment_version(version, rule).text


def test_version_show(tester):
    tester.execute()
    assert "simple-project 1.2.3\n" == tester.io.fetch_output()


def test_short_version_show(tester):
    tester.execute("--short")
    assert "1.2.3\n" == tester.io.fetch_output()


def test_version_update(tester):
    tester.execute("2.0.0")
    assert "Bumping version from 1.2.3 to 2.0.0\n" == tester.io.fetch_output()


def test_short_version_update(tester):
    tester.execute("--short 2.0.0")
    assert "2.0.0\n" == tester.io.fetch_output()
