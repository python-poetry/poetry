import os

from pathlib import Path

import pytest
import toml


@pytest.fixture()
def tester(command_tester_factory):
    return command_tester_factory("new")


def test_new(tmp_dir, tester):
    name = "foo"
    os.chdir(Path(tmp_dir).parent)
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
