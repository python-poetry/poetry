from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Callable

import pytest

from poetry.core.packages.dependency import Dependency
from poetry.core.packages.package import Package

from poetry.plugins.application_plugin import ApplicationPlugin
from poetry.plugins.plugin import Plugin
from poetry.utils._compat import metadata


if TYPE_CHECKING:
    from os import PathLike
    from pathlib import Path

    from cleo.io.io import IO
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.plugins.base_plugin import BasePlugin
    from poetry.poetry import Poetry
    from poetry.repositories import Repository
    from poetry.utils.env import Env
    from tests.helpers import PoetryTestApplication
    from tests.types import CommandTesterFactory


class DoNothingPlugin(Plugin):
    def activate(self, poetry: Poetry, io: IO) -> None:
        pass


class EntryPoint(metadata.EntryPoint):
    def load(self) -> type[BasePlugin]:
        if self.group == ApplicationPlugin.group:
            return ApplicationPlugin

        return DoNothingPlugin


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("self show plugins")


@pytest.fixture()
def plugin_package_requires_dist() -> list[str]:
    return []


@pytest.fixture()
def plugin_package(plugin_package_requires_dist: list[str]) -> Package:
    package = Package("poetry-plugin", "1.2.3")

    for requirement in plugin_package_requires_dist:
        package.add_dependency(Dependency.create_from_pep_508(requirement))

    return package


@pytest.fixture()
def plugin_distro(plugin_package: Package, tmp_path: Path) -> metadata.Distribution:
    class MockDistribution(metadata.Distribution):
        def read_text(self, filename: str) -> str | None:
            if filename == "METADATA":
                return "\n".join(
                    [
                        f"Name: {plugin_package.name}",
                        f"Version: {plugin_package.version}",
                        *[
                            f"Requires-Dist: {dep.to_pep_508()}"
                            for dep in plugin_package.requires
                        ],
                    ]
                )
            return None

        def locate_file(self, path: str | PathLike[str]) -> Path:
            return tmp_path / path

    return MockDistribution()  # type: ignore[no-untyped-call]


@pytest.fixture
def entry_point_name() -> str:
    return "poetry-plugin"


@pytest.fixture
def entry_point_values_by_group() -> dict[str, list[str]]:
    return {}


@pytest.fixture
def entry_points(
    entry_point_name: str,
    entry_point_values_by_group: dict[str, list[str]],
    plugin_distro: metadata.Distribution,
) -> Callable[..., list[metadata.EntryPoint]]:
    by_group = {
        key: [
            EntryPoint(  # type: ignore[no-untyped-call]
                name=entry_point_name,
                group=key,
                value=value,
            )._for(  # type: ignore[attr-defined]
                plugin_distro
            )
            for value in values
        ]
        for key, values in entry_point_values_by_group.items()
    }

    def _entry_points(**params: Any) -> list[metadata.EntryPoint]:
        group = params.get("group")

        if group not in by_group:
            return []

        eps: list[metadata.EntryPoint] = by_group[group]

        return eps

    return _entry_points


@pytest.fixture(autouse=True)
def mock_metadata_entry_points(
    plugin_package: Package,
    plugin_distro: metadata.Distribution,
    installed: Repository,
    mocker: MockerFixture,
    tmp_venv: Env,
    entry_points: Callable[..., metadata.EntryPoint],
) -> None:
    installed.add_package(plugin_package)

    mocker.patch.object(
        tmp_venv.site_packages, "find_distribution", return_value=plugin_distro
    )
    mocker.patch.object(metadata, "entry_points", entry_points)


@pytest.mark.parametrize("entry_point_name", ["poetry-plugin", "not-package-name"])
@pytest.mark.parametrize(
    "entry_point_values_by_group",
    [
        {
            ApplicationPlugin.group: ["FirstApplicationPlugin"],
            Plugin.group: ["FirstPlugin"],
        }
    ],
)
def test_show_displays_installed_plugins(
    app: PoetryTestApplication,
    tester: CommandTester,
) -> None:
    tester.execute("")

    expected = """
  - poetry-plugin (1.2.3)
      1 plugin and 1 application plugin
"""

    assert tester.io.fetch_output() == expected


@pytest.mark.parametrize(
    "entry_point_values_by_group",
    [
        {
            ApplicationPlugin.group: [
                "FirstApplicationPlugin",
                "SecondApplicationPlugin",
            ],
            Plugin.group: ["FirstPlugin", "SecondPlugin"],
        }
    ],
)
def test_show_displays_installed_plugins_with_multiple_plugins(
    app: PoetryTestApplication,
    tester: CommandTester,
) -> None:
    tester.execute("")

    expected = """
  - poetry-plugin (1.2.3)
      2 plugins and 2 application plugins
"""

    assert tester.io.fetch_output() == expected


@pytest.mark.parametrize(
    "plugin_package_requires_dist", [["foo (>=1.2.3)", "bar (<4.5.6)"]]
)
@pytest.mark.parametrize(
    "entry_point_values_by_group",
    [
        {
            ApplicationPlugin.group: ["FirstApplicationPlugin"],
            Plugin.group: ["FirstPlugin"],
        }
    ],
)
def test_show_displays_installed_plugins_with_dependencies(
    app: PoetryTestApplication,
    tester: CommandTester,
) -> None:
    tester.execute("")

    expected = """
  - poetry-plugin (1.2.3)
      1 plugin and 1 application plugin

      Dependencies
        - foo (>=1.2.3)
        - bar (<4.5.6)
"""

    assert tester.io.fetch_output() == expected
