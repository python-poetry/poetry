<<<<<<< HEAD
import sys

from pathlib import Path
from typing import TYPE_CHECKING
=======
from pathlib import Path
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

import pytest

from poetry.utils.env import MockEnv


<<<<<<< HEAD
if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from tests.types import CommandTesterFactory


@pytest.fixture(autouse=True)
def setup(mocker: "MockerFixture") -> None:
=======
@pytest.fixture(autouse=True)
def setup(mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    mocker.patch(
        "poetry.utils.env.EnvManager.get",
        return_value=MockEnv(
            path=Path("/prefix"), base=Path("/base/prefix"), is_venv=True
        ),
    )


@pytest.fixture
<<<<<<< HEAD
def tester(command_tester_factory: "CommandTesterFactory") -> "CommandTester":
    return command_tester_factory("env info")


def test_env_info_displays_complete_info(tester: "CommandTester"):
    tester.execute()

    expected = f"""
Virtualenv
Python:         3.7.0
Implementation: CPython
Path:           {Path('/prefix')}
Executable:     {sys.executable}
Valid:          True

System
Platform:   darwin
OS:         posix
Python:     {'.'.join(str(v) for v in sys.version_info[:3])}
Path:       {Path('/base/prefix')}
Executable: python
"""
=======
def tester(command_tester_factory):
    return command_tester_factory("env info")


def test_env_info_displays_complete_info(tester):
    tester.execute()

    expected = """
Virtualenv
Python:         3.7.0
Implementation: CPython
Path:           {prefix}
Valid:          True

System
Platform: darwin
OS:       posix
Python:   {base_prefix}
""".format(
        prefix=str(Path("/prefix")), base_prefix=str(Path("/base/prefix"))
    )
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

    assert expected == tester.io.fetch_output()


<<<<<<< HEAD
def test_env_info_displays_path_only(tester: "CommandTester"):
    tester.execute("--path")
    expected = str(Path("/prefix")) + "\n"
    assert tester.io.fetch_output() == expected
=======
def test_env_info_displays_path_only(tester):
    tester.execute("--path")
    expected = str(Path("/prefix"))
    assert expected + "\n" == tester.io.fetch_output()
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
