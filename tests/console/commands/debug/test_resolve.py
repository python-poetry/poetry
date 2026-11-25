from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.core.version.markers import parse_marker

from poetry.factory import Factory
from poetry.utils.env import MockEnv
from tests.helpers import get_package


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from tests.helpers import DummyRepository
    from tests.types import CommandTesterFactory


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("debug resolve")


@pytest.fixture(autouse=True)
def __add_packages(repo: DummyRepository) -> None:
    cachy020 = get_package("cachy", "0.2.0")
    cachy020.add_dependency(Factory.create_dependency("msgpack-python", ">=0.5 <0.6"))

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy020)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    repo.add_package(get_package("pendulum", "2.0.3"))
    repo.add_package(get_package("cleo", "0.6.5"))


def test_debug_resolve_gives_resolution_results(tester: CommandTester) -> None:
    tester.execute("cachy")

    expected = """\
Resolving dependencies...

Resolution results:

msgpack-python 0.5.3
cachy          0.2.0
"""

    assert tester.io.fetch_output() == expected


def test_debug_resolve_tree_option_gives_the_dependency_tree(
    tester: CommandTester,
) -> None:
    tester.execute("cachy --tree")

    expected = """\
Resolving dependencies...

Resolution results:

cachy 0.2.0
└── msgpack-python >=0.5 <0.6
"""

    assert tester.io.fetch_output() == expected


def test_debug_resolve_shows_marker_when_present(
    tester: CommandTester, repo: DummyRepository
) -> None:
    """Packages with environment markers must show the marker in output."""
    pkg = get_package("pathlib2", "2.3.0")
    pkg.marker = parse_marker('sys_platform == "win32"')
    repo.add_package(pkg)

    tester.execute("pathlib2")

    expected = """\
Resolving dependencies...

Resolution results:

pathlib2 2.3.0 sys_platform == "win32"
"""

    assert tester.io.fetch_output() == expected


def test_debug_resolve_git_dependency(tester: CommandTester) -> None:
    tester.execute("git+https://github.com/demo/demo.git")

    expected = """\
Resolving dependencies...

Resolution results:

pendulum 2.0.3
demo     0.1.2
"""

    assert tester.io.fetch_output() == expected


@pytest.mark.parametrize("install", [False, True])
@pytest.mark.parametrize("platform", ["linux", "win32"])
@pytest.mark.parametrize("python_version", [(3, 11, 0), (3, 12, 0)])
def test_debug_resolve_install_filters_dependencies_for_environment(
    tester: CommandTester,
    repo: DummyRepository,
    mocker: MockerFixture,
    install: bool,
    platform: str,
    python_version: tuple[int, int, int],
) -> None:
    package = get_package("app", "1.0")
    package.add_dependency(Factory.create_dependency("common-dep", "1.0"))
    package.add_dependency(
        Factory.create_dependency(
            "platform-dep", {"version": "1.0", "platform": "win32"}
        )
    )
    package.add_dependency(
        Factory.create_dependency("python-dep", {"version": "1.0", "python": "<3.12"})
    )
    repo.add_package(package)
    for name in ("common-dep", "platform-dep", "python-dep"):
        repo.add_package(get_package(name, "1.0"))

    mocker.patch(
        "poetry.utils.env.EnvManager.get",
        return_value=MockEnv(version_info=python_version, platform=platform),
    )

    assert tester.execute("app" + (" --install" if install else "")) == 0

    expected = {("app", "1.0"), ("common-dep", "1.0")}
    if not install or platform == "win32":
        expected.add(("platform-dep", "1.0"))
    if not install or python_version < (3, 12, 0):
        expected.add(("python-dep", "1.0"))

    output = tester.io.fetch_output().split("Resolution results:\n\n", 1)[1]
    assert {tuple(line.split()) for line in output.splitlines()} == expected
