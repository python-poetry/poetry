import pytest

from poetry.core.semver.version import Version
from tests.console.commands.env.helpers import check_output_wrapper


@pytest.fixture
def tester(command_tester_factory):
    return command_tester_factory("env remove")


def test_remove_by_python_version(
    mocker, tester, venvs_in_cache_dirs, venv_name, venv_cache
):
    check_output = mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )

    tester.execute("3.6")

    assert check_output.called
    assert not (venv_cache / f"{venv_name}-py3.6").exists()

    expected = f"Deleted virtualenv: {venv_cache / venv_name}-py3.6\n"
    assert expected == tester.io.fetch_output()


def test_remove_by_name(tester, venvs_in_cache_dirs, venv_name, venv_cache):
    expected = ""

    for name in venvs_in_cache_dirs:
        tester.execute(name)

        assert not (venv_cache / name).exists()

        expected += f"Deleted virtualenv: {venv_cache / name}\n"

    assert expected == tester.io.fetch_output()


def test_remove_all(tester, venvs_in_cache_dirs, venv_name, venv_cache):
    expected = {""}
    tester.execute("--all")
    for name in venvs_in_cache_dirs:
        assert not (venv_cache / name).exists()
        expected.add(f"Deleted virtualenv: {venv_cache / name}")
    assert expected == set(tester.io.fetch_output().split("\n"))


def test_remove_all_and_version(tester, venvs_in_cache_dirs, venv_name, venv_cache):
    expected = {""}
    tester.execute(f"--all {venvs_in_cache_dirs[0]}")
    for name in venvs_in_cache_dirs:
        assert not (venv_cache / name).exists()
        expected.add(f"Deleted virtualenv: {venv_cache / name}")
    assert expected == set(tester.io.fetch_output().split("\n"))


def test_remove_multiple(tester, venvs_in_cache_dirs, venv_name, venv_cache):
    expected = {""}
    removed_envs = venvs_in_cache_dirs[0:2]
    remaining_envs = venvs_in_cache_dirs[2:]
    tester.execute(" ".join(removed_envs))
    for name in removed_envs:
        assert not (venv_cache / name).exists()
        expected.add(f"Deleted virtualenv: {venv_cache / name}")
    for name in remaining_envs:
        assert (venv_cache / name).exists()
    assert expected == set(tester.io.fetch_output().split("\n"))
