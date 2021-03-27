import pytest
import tomlkit

from poetry.core.toml.file import TOMLFile


@pytest.fixture
def venv_activate_37(venv_cache, venv_name):
    envs_file = TOMLFile(venv_cache / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.0"}
    envs_file.write(doc)


@pytest.fixture
def tester(command_tester_factory):
    return command_tester_factory("env list")


def test_none_activated(tester, venvs_in_cache_dirs, mocker, env):
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=env)
    tester.execute()
    expected = "\n".join(venvs_in_cache_dirs).strip()
    assert expected == tester.io.fetch_output().strip()


def test_activated(tester, venvs_in_cache_dirs, venv_cache, venv_activate_37):
    tester.execute()
    expected = (
        "\n".join(venvs_in_cache_dirs).strip().replace("py3.7", "py3.7 (Activated)")
    )
    assert expected == tester.io.fetch_output().strip()


def test_in_project_venv(tester, venvs_in_project_dir):
    tester.execute()
    expected = ".venv (Activated)\n"
    assert expected == tester.io.fetch_output()
