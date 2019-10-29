import shutil
from glob import glob

import pytest
import tomlkit
from cleo.testers import CommandTester

from poetry.utils._compat import Path

fixtures_dir = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def setup():
    clear_new_project()

    yield

    clear_new_project()


def clear_new_project():
    shutil.rmtree(fixtures_dir / "new", ignore_errors=True)


@pytest.mark.parametrize(
    "format_param, readme",
    [("", "README.md"), ("--readme rst", "README.rst"), ("--readme md", "README.md")],
)
def test_new_command(app, format_param, readme):
    command = app.find("new")
    tester = CommandTester(command)
    tester.execute("{} {}".format(str(fixtures_dir / "new"), format_param))

    assert Path(fixtures_dir / "new").exists()

    expected_files = {
        fixtures_dir / "new/new",
        fixtures_dir / "new/new/__init__.py",
        fixtures_dir / "new/tests",
        fixtures_dir / "new/tests/__init__.py",
        fixtures_dir / "new/tests/test_new.py",
        fixtures_dir / "new/pyproject.toml",
        fixtures_dir / "new/{}".format(readme),
    }

    files = {
        Path(file) for file in glob(str(fixtures_dir / "new/**/*"), recursive=True)
    }

    assert sorted(files) == sorted(expected_files)

    with Path(fixtures_dir / "new/pyproject.toml").open() as toml:
        pyproject = tomlkit.parse(toml.read())

    assert pyproject["tool"]["poetry"]["name"] == "new"
    assert "version" in pyproject["tool"]["poetry"]
    assert "authors" in pyproject["tool"]["poetry"]
    assert "description" in pyproject["tool"]["poetry"]
    assert pyproject["tool"]["poetry"]["readme"] == readme

    assert "poetry>=0.12" in pyproject["build-system"]["requires"]
    assert pyproject["build-system"]["build-backend"] == "poetry.masonry.api"
