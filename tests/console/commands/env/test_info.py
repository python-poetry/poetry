import pytest

from cleo.testers import CommandTester

from poetry.utils._compat import Path
from poetry.utils.env import MockEnv


@pytest.fixture(autouse=True)
def setup(mocker):
    mocker.patch(
        "poetry.utils.env.EnvManager.get",
        return_value=MockEnv(
            path=Path("/prefix"), base=Path("/base/prefix"), is_venv=True
        ),
    )


def test_env_info_displays_complete_info(app):
    command = app.find("env:info")
    tester = CommandTester(command)

    tester.execute([("command", command.get_name())])

    expected = """
Virtualenv
==========

 * Python:         3.7.0
 * Implementation: CPython
 * Path:           {prefix}
 * Valid:          True


System
======

 * Platform: darwin
 * OS:       posix
 * Python:   {base_prefix}

""".format(
        prefix=str(Path("/prefix")), base_prefix=str(Path("/base/prefix"))
    )

    assert tester.get_display(True) == expected


def test_env_info_displays_path_only(app):
    command = app.find("env:info")
    tester = CommandTester(command)

    tester.execute([("command", command.get_name()), ("--path", True)])

    expected = str(Path("/prefix"))

    assert tester.get_display(True) == expected
