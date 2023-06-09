from __future__ import annotations

import os

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.core.utils.helpers import temporary_directory


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from tests.types import CommandTesterFactory


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("self init")


def test_init_no_args(
    tester: CommandTester,
) -> None:
    with temporary_directory() as tmp_dir:
        current_dir = os.getcwd()
        try:
            os.chdir(tmp_dir)
            tester.execute()
            assert tester.io.fetch_output() == f"""\
Initialising poetry settings for project {tmp_dir}
"""
            assert (Path(tmp_dir) / ".poetry" / "pyproject.toml").exists()
            assert tester.status_code == 0
        finally:
            os.chdir(current_dir)


def test_init_project_dir(
    tester: CommandTester,
) -> None:
    with temporary_directory() as tmp_dir:
        tester.execute(args=f"--project-dir {tmp_dir}")
        assert tester.io.fetch_output() == f"""\
Initialising poetry settings for project {tmp_dir}
"""
        assert (Path(tmp_dir) / ".poetry" / "pyproject.toml").exists()
        assert tester.status_code == 0


def test_init_project_dir_already_exists(
    tester: CommandTester,
) -> None:
    with temporary_directory() as tmp_dir:
        pyproject_file = Path(tmp_dir) / ".poetry" / "pyproject.toml"
        pyproject_file.parent.mkdir()
        pyproject_file.write_text("hello world")
        tester.execute(args=f"--project-dir {tmp_dir}")
        assert tester.io.fetch_output() == f"""\
Poetry settings already exist for project {tmp_dir}
"""
        assert tester.status_code == 1
