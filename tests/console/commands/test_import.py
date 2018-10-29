import pytest
import shutil

from cleo.testers import CommandTester

from poetry.poetry import Poetry
from poetry.utils._compat import Path
from poetry.console.commands.import_ import PipfileImporter


@pytest.fixture
def project_with_pipfile(tmpdir):
    src = Path(__file__).parent.parent.parent / "fixtures" / "project_with_pipfile"
    dest = Path(tmpdir) / "project_with_pipfile"
    shutil.copytree(str(src), str(dest))
    return dest


def test_import_file_does_not_exist(app, monkeypatch, project_with_pipfile):
    command = app.find("import")
    tester = CommandTester(command)
    monkeypatch.chdir(project_with_pipfile)
    rc = tester.execute([("command", command.get_name()), ("--from", "nosuch")])
    assert "does not exist" in tester.get_display(True)
    assert rc != 0


def test_unsupported_file(app, monkeypatch, project_with_pipfile):
    command = app.find("import")
    tester = CommandTester(command)
    monkeypatch.chdir(project_with_pipfile)
    (project_with_pipfile / "buildout.cfg").touch()
    rc = tester.execute([("command", command.get_name()), ("--from", "buildout.cfg")])
    assert "Unsupported" in tester.get_display(True)
    assert rc != 0


def test_basic_import(app, mocker, monkeypatch, project_with_pipfile):
    command = app.find("import")

    tester = CommandTester(command)

    monkeypatch.chdir(project_with_pipfile)
    tester.execute(
        [
            ("command", command.get_name()),
            ("--from", "Pipfile"),
            ("--package-name", "foobar"),
            ("--package-version", "0.3"),
        ]
    )

    assert "Importing from Pipfile" in tester.get_display(True)

    # Assert generated config is valid:
    Poetry.create(project_with_pipfile)


def test_pipfile_empty():
    pipfile_data = {}
    importer = PipfileImporter("foo", "0.1", pipfile_data)
    layout = importer.get_layout()
    assert layout


def test_fetch_data():
    pipfile_data = {
        "packages": {"pendulum": "*"},
        "dev-packages": {"pytest": ">= 3.2"},
        "requires": {"python_version": "3.6"},
    }
    importer = PipfileImporter("foo", "0.1", pipfile_data)

    deps = importer.get_deps()
    assert deps == {"pendulum": "*"}

    assert importer.get_required_python() == "3.6"

    dev_deps = importer.get_dev_deps()
    assert dev_deps["pytest"] == ">= 3.2"


def test_fetch_git_packages():
    pipfile_data = {
        "packages": {
            "foo": {
                "git": "ssh://git@example.com/foo",
                "ref": "ed2e1d51c893cfc9c9253fe6717be262e6215007",
            }
        }
    }
    importer = PipfileImporter("foo", "0.1", pipfile_data)
    deps = importer.get_deps()

    assert deps["foo"] == {
        "git": "ssh://git@example.com/foo",
        "rev": "ed2e1d51c893cfc9c9253fe6717be262e6215007",
    }


def assert_git_convert(version, expected):
    actual = PipfileImporter.convert_git_version(version)
    assert actual == expected


def test_convert_rev_to_ref():
    version = {"git": "http://git/foo.git", "ref": "0bc42"}
    expected = {"git": "http://git/foo.git", "rev": "0bc42"}
    assert_git_convert(version, expected)

    version = {"git": "http://git/foo.git", "branch": "master"}
    expected = {"git": "http://git/foo.git", "branch": "master"}
    assert_git_convert(version, expected)


def test_drop_editable():
    version = {"git": "http://git/foo.git", "ref": "0bc42", "editable": True}
    expected = {"git": "http://git/foo.git", "rev": "0bc42"}
    assert_git_convert(version, expected)
