import os
import shutil

from pathlib import Path

import pytest
import toml


@pytest.fixture()
def tester(command_tester_factory):
    return command_tester_factory("new")


@pytest.fixture()
def project_root(tmp_dir):
    dir = Path(tmp_dir) / "project_root"
    dir.mkdir()
    cwd = Path().cwd()
    os.chdir(dir)
    yield dir
    os.chdir(cwd)
    shutil.rmtree(dir)


def test_new(tmp_dir, tester, project_root):
    name = "foo_boo_bar"
    tester.execute(f" . --name {name}")
    pyproject = project_root / "pyproject.toml"
    assert pyproject.is_file()
    assert (project_root / name).is_dir()
    assert (project_root / name / "__init__.py").is_file()
    assert (project_root / "tests").is_dir()
    assert (project_root / "README.rst").is_file()
    with pyproject.open() as f:
        pyproject_data = toml.load(f)
    assert pyproject_data["tool"]["poetry"]["name"] == name
    assert pyproject_data["tool"]["poetry"]["version"] == "0.1.0"
    assert "pytest" in pyproject_data["tool"]["poetry"]["dev-dependencies"]
