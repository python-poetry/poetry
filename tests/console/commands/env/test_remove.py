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
    assert not (venv_cache / "{}-py3.6".format(venv_name)).exists()

    expected = "Deleted virtualenv: {}\n".format(
        (venv_cache / "{}-py3.6".format(venv_name))
    )
    assert expected == tester.io.fetch_output()


def test_remove_by_name(tester, venvs_in_cache_dirs, venv_name, venv_cache):
    expected = ""

    for name in venvs_in_cache_dirs:
        tester.execute(name)

        assert not (venv_cache / name).exists()

        expected += "Deleted virtualenv: {}\n".format((venv_cache / name))

    assert expected == tester.io.fetch_output()
