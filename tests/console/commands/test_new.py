import os

from pathlib import Path

import pytest
import toml


@pytest.fixture()
def tester(command_tester_factory):
    return command_tester_factory("new")


@pytest.fixture()
def cd_root(tmp_dir):
    cwd = Path().cwd()
    yield os.chdir(Path(tmp_dir).parent)
    os.chdir(cwd)


def test_new(tmp_dir, tester, cd_root):
    name = "foo_boo_bar"
    tester.execute(f"{tmp_dir} --name {name}")
    pyproject = Path(tmp_dir) / "pyproject.toml"
    assert pyproject.is_file()
    assert (Path(tmp_dir) / name).is_dir()
    assert (Path(tmp_dir) / name / "__init__.py").is_file()
    assert (Path(tmp_dir) / "tests").is_dir()
    assert (Path(tmp_dir) / "README.rst").is_file()
    with pyproject.open() as f:
        pyproject_data = toml.load(f)
    assert pyproject_data["tool"]["poetry"]["name"] == name
    assert pyproject_data["tool"]["poetry"]["version"] == "0.1.0"
    assert "pytest" in pyproject_data["tool"]["poetry"]["dev-dependencies"]


#
