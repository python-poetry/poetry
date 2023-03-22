from __future__ import annotations

import pytest

from poetry.core.packages.dependency import Dependency
from poetry.core.packages.package import Package
from poetry.core.packages.project_package import ProjectPackage

from poetry.__version__ import __version__
from poetry.console.commands.self.self_command import SelfCommand
from poetry.factory import Factory


@pytest.fixture
def example_system_pyproject():
    package = ProjectPackage("poetry-instance", __version__)
    plugin = Package("poetry-plugin", "1.2.3")

    package.add_dependency(
        Dependency(plugin.name, "^1.2.3", groups=[SelfCommand.ADDITIONAL_PACKAGE_GROUP])
    )
    content = Factory.create_pyproject_from_package(package)
    return content.as_string()[:-2]  # remove trailing newlines


@pytest.mark.parametrize("existing_newlines", [0, 2])
def test_generate_system_pyproject_trailing_newline(
    existing_newlines: int,
    example_system_pyproject: str,
):
    cmd = SelfCommand()
    cmd.system_pyproject.write_text(example_system_pyproject + "\n" * existing_newlines)
    cmd.generate_system_pyproject()
    generated = cmd.system_pyproject.read_text()

    for _i, c in enumerate(generated[::-1]):
        if c != "\n":
            break

    assert (existing_newlines < 2 and _i == 1) or (
        existing_newlines > 1 and _i == existing_newlines
    )


def test_generate_system_pyproject_carraige_returns(
    example_system_pyproject: str,
):
    cmd = SelfCommand()
    cmd.system_pyproject.write_text(example_system_pyproject + "\n")
    cmd.generate_system_pyproject()

    with open(cmd.system_pyproject, newline="") as f:  # do not translate newlines
        generated = f.read()

    assert "\r\r" not in generated
