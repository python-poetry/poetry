from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.core.constraints.version import Version

from tests.console.commands.env.helpers import check_output_wrapper


if TYPE_CHECKING:
    from pathlib import Path

    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("env remove")


def test_remove_by_python_version(
    mocker: MockerFixture,
    tester: CommandTester,
    venvs_in_cache_dirs: list[str],
    venv_name: str,
    venv_cache: Path,
) -> None:
    check_output = mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )

    tester.execute("3.6")

    assert check_output.called
    assert not (venv_cache / f"{venv_name}-py3.6").exists()

    expected = f"Deleted virtualenv: {venv_cache / venv_name}-py3.6\n"
    assert tester.io.fetch_output() == expected


def test_remove_by_name(
    tester: CommandTester,
    venvs_in_cache_dirs: list[str],
    venv_name: str,
    venv_cache: Path,
) -> None:
    expected = ""

    for name in venvs_in_cache_dirs:
        tester.execute(name)

        assert not (venv_cache / name).exists()

        expected += f"Deleted virtualenv: {venv_cache / name}\n"

    assert tester.io.fetch_output() == expected


@pytest.mark.parametrize(
    "envs_file", [None, "empty", "self", "other", "self_and_other"]
)
def test_remove_all(
    tester: CommandTester,
    venvs_in_cache_dirs: list[str],
    venv_name: str,
    venv_cache: Path,
    envs_file: str | None,
) -> None:
    envs_file_path = venv_cache / "envs.toml"
    if envs_file == "empty":
        envs_file_path.touch()
    elif envs_file == "self":
        envs_file_path.write_text(f'[{venv_name}]\nminor = "3.9"\npatch = "3.9.1"\n')
    elif envs_file == "other":
        envs_file_path.write_text('[other-abcdefgh]\nminor = "3.9"\npatch = "3.9.1"\n')
    elif envs_file == "self_and_other":
        envs_file_path.write_text(
            f'[{venv_name}]\nminor = "3.9"\npatch = "3.9.1"\n'
            '[other-abcdefgh]\nminor = "3.9"\npatch = "3.9.1"\n'
        )
    else:
        # no envs file -> nothing to prepare
        assert envs_file is None

    expected = {""}
    tester.execute("--all")
    for name in venvs_in_cache_dirs:
        assert not (venv_cache / name).exists()
        expected.add(f"Deleted virtualenv: {venv_cache / name}")
    assert set(tester.io.fetch_output().split("\n")) == expected

    if envs_file is not None:
        assert envs_file_path.exists()
        envs_file_content = envs_file_path.read_text()
        assert venv_name not in envs_file_content
        if "other" in envs_file:
            assert "other-abcdefgh" in envs_file_content
        else:
            assert envs_file_content == ""
    else:
        assert not envs_file_path.exists()


def test_remove_all_and_version(
    tester: CommandTester,
    venvs_in_cache_dirs: list[str],
    venv_name: str,
    venv_cache: Path,
) -> None:
    expected = {""}
    tester.execute(f"--all {venvs_in_cache_dirs[0]}")
    for name in venvs_in_cache_dirs:
        assert not (venv_cache / name).exists()
        expected.add(f"Deleted virtualenv: {venv_cache / name}")
    assert set(tester.io.fetch_output().split("\n")) == expected


def test_remove_multiple(
    tester: CommandTester,
    venvs_in_cache_dirs: list[str],
    venv_name: str,
    venv_cache: Path,
) -> None:
    expected = {""}
    removed_envs = venvs_in_cache_dirs[0:2]
    remaining_envs = venvs_in_cache_dirs[2:]
    tester.execute(" ".join(removed_envs))
    for name in removed_envs:
        assert not (venv_cache / name).exists()
        expected.add(f"Deleted virtualenv: {venv_cache / name}")
    for name in remaining_envs:
        assert (venv_cache / name).exists()
    assert set(tester.io.fetch_output().split("\n")) == expected
