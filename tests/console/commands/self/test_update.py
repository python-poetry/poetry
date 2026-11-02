from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.core.constraints.version import Version
from poetry.core.packages.dependency_group import MAIN_GROUP
from poetry.core.packages.package import Package
from poetry.core.packages.project_package import ProjectPackage
from poetry.core.version.markers import AnyMarker

from poetry.__version__ import __version__
from poetry.factory import Factory
from poetry.installation.executor import Executor
from poetry.installation.wheel_installer import WheelInstaller
from poetry.packages.locker import Locker
from poetry.packages.transitive_package_info import TransitivePackageInfo
from poetry.utils.constants import POETRY_SYSTEM_PROJECT_NAME


if TYPE_CHECKING:
    from pathlib import Path

    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from tests.helpers import DummyRepository
    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter


@pytest.fixture
def setup(mocker: MockerFixture, fixture_dir: FixtureDirGetter) -> None:
    mocker.patch.object(
        Executor,
        "_download",
        return_value=fixture_dir("distributions").joinpath(
            "demo-0.1.2-py2.py3-none-any.whl"
        ),
    )

    mocker.patch.object(WheelInstaller, "install")


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("self update")


def test_self_update_can_update_from_recommended_installation(
    tester: CommandTester,
    repo: DummyRepository,
    installed: DummyRepository,
) -> None:
    new_version = Version.parse(__version__).next_minor().text

    old_poetry = Package("poetry", __version__)
    old_poetry.add_dependency(Factory.create_dependency("cleo", "^0.8.2"))

    new_poetry = Package("poetry", new_version)
    new_poetry.add_dependency(Factory.create_dependency("cleo", "^1.0.0"))

    installed.add_package(old_poetry)
    installed.add_package(Package("cleo", "0.8.2"))

    repo.add_package(new_poetry)
    repo.add_package(Package("cleo", "1.0.0"))

    tester.execute()

    expected_output = f"""\
Updating Poetry version ...

Using version ^{new_version} for poetry

Updating dependencies
Resolving dependencies...

Package operations: 0 installs, 2 updates, 0 removals

  - Updating cleo (0.8.2 -> 1.0.0)
  - Updating poetry ({__version__} -> {new_version})

Writing lock file
"""

    assert tester.io.fetch_output() == expected_output


def test_self_update_does_not_downgrade_dependencies_from_outdated_lock_file(
    tester: CommandTester,
    repo: DummyRepository,
    installed: DummyRepository,
    config_dir: Path,
) -> None:
    new_version = Version.parse(__version__).next_minor().text

    old_poetry = Package("poetry", __version__)
    old_poetry.add_dependency(Factory.create_dependency("cleo", ">=0.8.2"))

    new_poetry = Package("poetry", new_version)
    new_poetry.add_dependency(Factory.create_dependency("cleo", ">=0.8.2"))

    installed.add_package(old_poetry)
    installed.add_package(Package("cleo", "1.0.0"))

    repo.add_package(new_poetry)
    repo.add_package(Package("cleo", "0.8.2"))
    repo.add_package(Package("cleo", "1.0.0"))

    # a lock file that has been written by an older Poetry version
    locker = Locker(config_dir / "poetry.lock", {})
    locker.set_lock_data(
        ProjectPackage(POETRY_SYSTEM_PROJECT_NAME, __version__),
        {
            package: TransitivePackageInfo(0, {MAIN_GROUP}, {MAIN_GROUP: AnyMarker()})
            for package in (old_poetry, Package("cleo", "0.8.2"))
        },
    )

    tester.execute()

    expected_output = f"""\
Updating Poetry version ...

Using version ^{new_version} for poetry

Updating dependencies
Resolving dependencies...

Package operations: 0 installs, 1 update, 0 removals

  - Updating poetry ({__version__} -> {new_version})

Writing lock file
"""

    assert tester.io.fetch_output() == expected_output


def test_self_update_updates_additional_packages(
    command_tester_factory: CommandTesterFactory,
    repo: DummyRepository,
    installed: DummyRepository,
) -> None:
    repo.add_package(Package("poetry-plugin", "0.1.0"))
    command_tester_factory("self add").execute("poetry-plugin")
    installed.add_package(Package("poetry-plugin", "0.1.0"))

    new_version = Version.parse(__version__).next_minor().text
    repo.add_package(Package("poetry", new_version))
    repo.add_package(Package("poetry-plugin", "0.1.1"))

    tester = command_tester_factory("self update")
    tester.execute()

    expected_output = f"""\
Updating Poetry version ...

Using version ^{new_version} for poetry

Updating dependencies
Resolving dependencies...

Package operations: 0 installs, 2 updates, 0 removals

  - Updating poetry ({__version__} -> {new_version})
  - Updating poetry-plugin (0.1.0 -> 0.1.1)

Writing lock file
"""

    assert tester.io.fetch_output() == expected_output
