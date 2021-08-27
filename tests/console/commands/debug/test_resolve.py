<<<<<<< HEAD
from typing import TYPE_CHECKING

=======
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
import pytest

from poetry.factory import Factory
from tests.helpers import get_package


<<<<<<< HEAD
if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from tests.helpers import TestRepository
    from tests.types import CommandTesterFactory


@pytest.fixture()
def tester(command_tester_factory: "CommandTesterFactory") -> "CommandTester":
=======
@pytest.fixture()
def tester(command_tester_factory):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return command_tester_factory("debug resolve")


@pytest.fixture(autouse=True)
<<<<<<< HEAD
def __add_packages(repo: "TestRepository") -> None:
=======
def __add_packages(repo):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    cachy020 = get_package("cachy", "0.2.0")
    cachy020.add_dependency(Factory.create_dependency("msgpack-python", ">=0.5 <0.6"))

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy020)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    repo.add_package(get_package("pendulum", "2.0.3"))
    repo.add_package(get_package("cleo", "0.6.5"))


<<<<<<< HEAD
def test_debug_resolve_gives_resolution_results(tester: "CommandTester"):
=======
def test_debug_resolve_gives_resolution_results(tester):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    tester.execute("cachy")

    expected = """\
Resolving dependencies...

Resolution results:

<<<<<<< HEAD
msgpack-python 0.5.3
cachy          0.2.0
=======
msgpack-python 0.5.3 
cachy          0.2.0 
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
"""

    assert expected == tester.io.fetch_output()


<<<<<<< HEAD
def test_debug_resolve_tree_option_gives_the_dependency_tree(tester: "CommandTester"):
=======
def test_debug_resolve_tree_option_gives_the_dependency_tree(tester):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    tester.execute("cachy --tree")

    expected = """\
Resolving dependencies...

Resolution results:

cachy 0.2.0
└── msgpack-python >=0.5 <0.6
"""

    assert expected == tester.io.fetch_output()


<<<<<<< HEAD
def test_debug_resolve_git_dependency(tester: "CommandTester"):
=======
def test_debug_resolve_git_dependency(tester):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    tester.execute("git+https://github.com/demo/demo.git")

    expected = """\
Resolving dependencies...

Resolution results:

<<<<<<< HEAD
pendulum 2.0.3
demo     0.1.2
=======
pendulum 2.0.3 
demo     0.1.2 
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
"""

    assert expected == tester.io.fetch_output()
