import pytest

from cleo import CommandTester

from poetry.console.commands import VersionCommand
from poetry.console.commands.version import VersionFinder
from poetry.factory import Factory
from poetry.semver import Version
from poetry.utils._compat import Path


@pytest.fixture()
def command():
    return VersionCommand()


@pytest.fixture()
def setup_project(app, mocker):
    def make(root, version=None):
        poetry = Factory().create_poetry(root)
        app._poetry = poetry
        if version:
            poetry.package._version = Version.parse(version)
            poetry.package._pretty_version = poetry.package._version.text

        mocker.patch("tomlkit.toml_file.TOMLFile.write")
        mocker.patch.object(Path, "write_text")
        return poetry

    return make


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


def test_version_show(app):
    command = app.find("version")
    tester = CommandTester(command)
    tester.execute()
    assert "Project (simple-project) version is 1.2.3\n" == tester.io.fetch_output()


@pytest.mark.parametrize(
    "file_content, expected",
    [
        ("__version__='1.0.0'", "1.0.0"),
        ('__version__="1.0.0"', "1.0.0"),
        ('__version__ = "1.0.0"', "1.0.0"),
        ('__version__ version = "1.0.0"', "1.0.0"),
        ('foo = 1\n__version__="1.0.0"', "1.0.0"),
        ("__version__=\"1.2.3\"\nbar = 'bar'", "1.2.3"),
        ("foo = 1\n__version__=\"1.2.3\"\nbar = 'bar'", "1.2.3"),
        ("if True:\n  __version__=\"1.2.3\"\nbar = 'bar'", "1.2.3"),
    ],
)
def test_version_matcher(file_content, expected):
    finder = VersionFinder("foo", Path("bar"))
    match = finder.version_var_re.match(file_content)
    assert match.group(2) == expected


@pytest.mark.parametrize(
    "file, expected",
    [
        ('foo = 1__version__="1.2.3"', "1.2.3"),
        ("foo = '__version__=\"1.2.3\"'", "1.2.3"),
    ],
)
def test_version_matcher_bad_files(file, expected):
    finder = VersionFinder("foo", Path("bar"))
    match = finder.version_var_re.match(file)
    assert not match


def test_version_sync_guess_file(app, fixture_dir, setup_project):
    root = fixture_dir("version_sync") / "with_script"
    setup_project(root)
    command = app.find("version")
    tester = CommandTester(command)
    tester.execute("--sync")
    expected = """\
Project (my-package) version is 1.2.3
Versions are already in sync.
"""
    assert expected == tester.io.fetch_output()


def test_version_sync_file_not_found(app, fixture_dir, setup_project):
    root = fixture_dir("version_sync") / "not_found"
    setup_project(root)
    command = app.find("version")
    tester = CommandTester(command)
    tester.execute("--sync")
    expected = """\
Project (my-package) version is 1.2.3
__version__ wasn't found.
"""
    assert expected == tester.io.fetch_output()


def test_version_sync_guess_module(app, fixture_dir, setup_project):
    root = fixture_dir("version_sync") / "with_module"
    setup_project(root)
    command = app.find("version")
    tester = CommandTester(command)
    tester.execute("--sync")
    expected = """\
Project (my-package) version is 1.2.3
Versions are already in sync.
"""
    assert expected == tester.io.fetch_output()


def test_version_sync_update_from_config(app, fixture_dir, setup_project):
    root = fixture_dir("version_sync") / "with_module"
    version_file = root / "my_package" / "__init__.py"
    setup_project(root, "1.2.4")

    command = app.find("version")
    tester = CommandTester(command)
    tester.execute("--sync")
    expected = """\
Project (my-package) version is 1.2.4
Changing __version__ ({}) to 1.2.4
"""
    expected = expected.format(version_file)
    assert expected == tester.io.fetch_output()


def test_version_sync_update_both(app, fixture_dir, setup_project):
    root = fixture_dir("version_sync") / "with_module"
    version_file = root / "my_package" / "__init__.py"
    setup_project(root)

    command = app.find("version")
    tester = CommandTester(command)
    tester.execute("patch --sync")
    expected = """\
Bumping version from 1.2.3 to 1.2.4
Changing __version__ ({}) to 1.2.4
"""
    expected = expected.format(version_file)
    assert expected == tester.io.fetch_output()


def test_version_sync_specified_file(app, fixture_dir, setup_project):
    root = fixture_dir("version_sync") / "with_module"
    version_file = root / "my_package" / "foo.py"
    setup_project(root)

    command = app.find("version")
    tester = CommandTester(command)
    tester.execute("--sync {}".format(version_file))
    expected = """\
Project (my-package) version is 1.2.3
Versions are already in sync.
"""
    assert expected == tester.io.fetch_output()


def test_version_sync_specified_file_update(app, fixture_dir, setup_project):
    root = fixture_dir("version_sync") / "with_module"
    version_file = root / "my_package" / "foo.py"
    setup_project(root, "2.0")

    command = app.find("version")
    tester = CommandTester(command)
    tester.execute("--sync {}".format(version_file))
    expected = """\
Project (my-package) version is 2.0
Changing __version__ ({}) to 2.0
"""
    expected = expected.format(version_file)
    assert expected == tester.io.fetch_output()
