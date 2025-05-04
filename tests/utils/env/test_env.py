from __future__ import annotations

import os
import re
import subprocess
import sys

from pathlib import Path
from threading import Thread
from typing import TYPE_CHECKING

import packaging.tags
import pytest

from deepdiff.diff import DeepDiff
from installer.utils import SCHEME_NAMES

from poetry.factory import Factory
from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils._compat import WINDOWS
from poetry.utils._compat import metadata
from poetry.utils.env import EnvCommandError
from poetry.utils.env import EnvManager
from poetry.utils.env import GenericEnv
from poetry.utils.env import MockEnv
from poetry.utils.env import SystemEnv
from poetry.utils.env import VirtualEnv
from poetry.utils.env import build_environment
from poetry.utils.env import ephemeral_environment
from poetry.utils.helpers import is_dir_writable


if TYPE_CHECKING:
    from collections.abc import Iterator

    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry
    from tests.types import FixtureDirGetter
    from tests.types import SetProjectContext

MINIMAL_SCRIPT = """\

print("Minimal Output"),
"""

# Script expected to fail.
ERRORING_SCRIPT = """\
import nullpackage

print("nullpackage loaded"),
"""


class MockVirtualEnv(VirtualEnv):
    def __init__(
        self,
        path: Path,
        base: Path | None = None,
        sys_path: list[str] | None = None,
    ) -> None:
        super().__init__(path, base=base)

        self._sys_path = sys_path

    @property
    def sys_path(self) -> list[str]:
        if self._sys_path is not None:
            return self._sys_path

        return super().sys_path


def test_virtualenvs_with_spaces_in_their_path_work_as_expected(
    tmp_path: Path, manager: EnvManager
) -> None:
    venv_path = tmp_path / "Virtual Env"

    manager.build_venv(venv_path)

    venv = VirtualEnv(venv_path)

    assert venv.run("python", "-V").startswith("Python")


def test_env_commands_with_spaces_in_their_arg_work_as_expected(
    tmp_path: Path, manager: EnvManager
) -> None:
    venv_path = tmp_path / "Virtual Env"
    manager.build_venv(venv_path)
    venv = VirtualEnv(venv_path)
    output = venv.run("python", str(venv.pip), "--version")
    assert re.match(r"pip \S+ from", output)


@pytest.mark.parametrize("differing_platform", [True, False])
def test_env_get_supported_tags_matches_inside_virtualenv(
    tmp_path: Path, manager: EnvManager, mocker: MockerFixture, differing_platform: bool
) -> None:
    venv_path = tmp_path / "Virtual Env"
    manager.build_venv(venv_path)
    venv = VirtualEnv(venv_path)

    run_python_script_spy = mocker.spy(venv, "run_python_script")

    # determine expected tags before patching sysconfig!
    expected_tags = list(packaging.tags.sys_tags())

    if differing_platform:
        mocker.patch("sysconfig.get_platform", return_value="some_other_platform")
        expected_call_count = 2
    else:
        expected_call_count = 1

    assert venv.get_supported_tags() == expected_tags
    assert run_python_script_spy.call_count == expected_call_count


@pytest.mark.skipif(os.name == "nt", reason="Symlinks are not support for Windows")
def test_env_has_symlinks_on_nix(tmp_path: Path, tmp_venv: VirtualEnv) -> None:
    assert os.path.islink(tmp_venv.python)


def test_run_with_keyboard_interrupt(
    tmp_path: Path, tmp_venv: VirtualEnv, mocker: MockerFixture
) -> None:
    mocker.patch("subprocess.check_output", side_effect=KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        tmp_venv.run("python", "-c", MINIMAL_SCRIPT)
    subprocess.check_output.assert_called_once()  # type: ignore[attr-defined]


def test_call_with_keyboard_interrupt(
    tmp_path: Path, tmp_venv: VirtualEnv, mocker: MockerFixture
) -> None:
    mocker.patch("subprocess.check_call", side_effect=KeyboardInterrupt())
    kwargs = {"call": True}
    with pytest.raises(KeyboardInterrupt):
        tmp_venv.run("python", "-", **kwargs)
    subprocess.check_call.assert_called_once()  # type: ignore[attr-defined]


def test_run_with_called_process_error(
    tmp_path: Path, tmp_venv: VirtualEnv, mocker: MockerFixture
) -> None:
    mocker.patch(
        "subprocess.check_output",
        side_effect=subprocess.CalledProcessError(
            42, "some_command", "some output", "some error"
        ),
    )
    with pytest.raises(EnvCommandError) as error:
        tmp_venv.run("python", "-c", MINIMAL_SCRIPT)
    subprocess.check_output.assert_called_once()  # type: ignore[attr-defined]
    assert "some output" in str(error.value)
    assert "some error" in str(error.value)


def test_call_no_input_with_called_process_error(
    tmp_path: Path, tmp_venv: VirtualEnv, mocker: MockerFixture
) -> None:
    mocker.patch(
        "subprocess.check_call",
        side_effect=subprocess.CalledProcessError(
            42, "some_command", "some output", "some error"
        ),
    )
    kwargs = {"call": True}
    with pytest.raises(EnvCommandError) as error:
        tmp_venv.run("python", "-", **kwargs)
    subprocess.check_call.assert_called_once()  # type: ignore[attr-defined]
    assert "some output" in str(error.value)
    assert "some error" in str(error.value)


def test_check_output_with_called_process_error(
    tmp_path: Path, tmp_venv: VirtualEnv, mocker: MockerFixture
) -> None:
    mocker.patch(
        "subprocess.check_output",
        side_effect=subprocess.CalledProcessError(
            42, "some_command", "some output", "some error"
        ),
    )
    with pytest.raises(EnvCommandError) as error:
        tmp_venv.run("python", "-")
    subprocess.check_output.assert_called_once()  # type: ignore[attr-defined]
    assert "some output" in str(error.value)
    assert "some error" in str(error.value)


@pytest.mark.parametrize("out", ["sys.stdout", "sys.stderr"])
def test_call_does_not_block_on_full_pipe(
    tmp_path: Path, tmp_venv: VirtualEnv, out: str
) -> None:
    """see https://github.com/python-poetry/poetry/issues/7698"""
    script = tmp_path / "script.py"
    script.write_text(
        f"""\
import sys
for i in range(10000):
    print('just print a lot of text to fill the buffer', file={out})
""",
        encoding="utf-8",
    )

    def target(result: list[int]) -> None:
        tmp_venv.run("python", str(script), call=True)
        result.append(0)

    results: list[int] = []
    # use a separate thread, so that the test does not block in case of error
    thread = Thread(target=target, args=(results,))
    thread.start()
    thread.join(1)  # must not block
    assert results and results[0] == 0


def test_run_python_script_called_process_error(
    tmp_path: Path, tmp_venv: VirtualEnv, mocker: MockerFixture
) -> None:
    mocker.patch(
        "subprocess.run",
        side_effect=subprocess.CalledProcessError(
            42, "some_command", "some output", "some error"
        ),
    )
    with pytest.raises(EnvCommandError) as error:
        tmp_venv.run_python_script(MINIMAL_SCRIPT)
    assert "some output" in str(error.value)
    assert "some error" in str(error.value)


def test_run_python_script_only_stdout(tmp_path: Path, tmp_venv: VirtualEnv) -> None:
    output = tmp_venv.run_python_script(
        "import sys; print('some warning', file=sys.stderr); print('some output')"
    )
    assert "some output" in output
    assert "some warning" not in output


def test_system_env_has_correct_paths() -> None:
    env = SystemEnv(Path(sys.prefix))

    paths = env.paths

    assert paths.get("purelib") is not None
    assert paths.get("platlib") is not None
    assert paths.get("scripts") is not None
    assert env.site_packages.path == Path(paths["purelib"])
    assert paths["include"] is not None


@pytest.mark.parametrize(
    "enabled",
    [True, False],
)
def test_system_env_usersite(mocker: MockerFixture, enabled: bool) -> None:
    mocker.patch("site.check_enableusersite", return_value=enabled)
    env = SystemEnv(Path(sys.prefix))
    assert (enabled and env.usersite is not None) or (
        not enabled and env.usersite is None
    )


def test_venv_has_correct_paths(tmp_venv: VirtualEnv) -> None:
    paths = tmp_venv.paths

    assert paths.get("purelib") is not None
    assert paths.get("platlib") is not None
    assert paths.get("scripts") is not None
    assert tmp_venv.site_packages.path == Path(paths["purelib"])
    assert paths["include"] == str(
        tmp_venv.path.joinpath(
            f"include/site/python{tmp_venv.version_info[0]}.{tmp_venv.version_info[1]}"
        )
    )


@pytest.mark.parametrize("with_system_site_packages", [True, False])
def test_env_system_packages(
    tmp_path: Path, poetry: Poetry, with_system_site_packages: bool
) -> None:
    venv_path = tmp_path / "venv"
    pyvenv_cfg = venv_path / "pyvenv.cfg"

    EnvManager(poetry).build_venv(
        path=venv_path, flags={"system-site-packages": with_system_site_packages}
    )
    env = VirtualEnv(venv_path)

    assert (
        f"include-system-site-packages = {str(with_system_site_packages).lower()}"
        in pyvenv_cfg.read_text(encoding="utf-8")
    )
    assert env.includes_system_site_packages is with_system_site_packages


def test_generic_env_system_packages(poetry: Poetry) -> None:
    """https://github.com/python-poetry/poetry/issues/8646"""
    env = GenericEnv(Path(sys.base_prefix))
    assert not env.includes_system_site_packages


@pytest.mark.parametrize("with_system_site_packages", [True, False])
def test_env_system_packages_are_relative_to_lib(
    tmp_path: Path, poetry: Poetry, with_system_site_packages: bool
) -> None:
    venv_path = tmp_path / "venv"
    EnvManager(poetry).build_venv(
        path=venv_path, flags={"system-site-packages": with_system_site_packages}
    )
    env = VirtualEnv(venv_path)

    # These are Poetry's own dependencies.
    # They should not be relative to the virtualenv's lib directory.
    for dist in metadata.distributions():
        assert not env.is_path_relative_to_lib(
            Path(str(dist._path))  # type: ignore[attr-defined]
        )
        # Checking one package is sufficient
        break
    else:
        pytest.fail("No distributions found in Poetry's own environment")

    # These are the virtual environments' base env packages,
    # in this case the system site packages.
    for dist in env.parent_env.site_packages.distributions():
        assert (
            env.is_path_relative_to_lib(
                Path(str(dist._path))  # type: ignore[attr-defined]
            )
            is with_system_site_packages
        )
        # Checking one package is sufficient
        break
    else:
        pytest.fail("No distributions found in the base environment of the virtualenv")


@pytest.mark.parametrize(
    ("flags", "packages"),
    [
        ({"no-pip": False}, {"pip"}),
        ({"no-pip": True}, set()),
        ({}, set()),
    ],
)
def test_env_no_pip(
    tmp_path: Path, poetry: Poetry, flags: dict[str, str | bool], packages: set[str]
) -> None:
    venv_path = tmp_path / "venv"
    EnvManager(poetry).build_venv(path=venv_path, flags=flags)
    env = VirtualEnv(venv_path)
    installed_repository = InstalledRepository.load(env=env, with_dependencies=True)
    installed_packages = {
        package.name
        for package in installed_repository.packages
        # workaround for BSD test environments
        if package.name != "sqlite3"
    }

    assert installed_packages == packages


def test_env_finds_the_correct_executables(tmp_path: Path, manager: EnvManager) -> None:
    venv_path = tmp_path / "Virtual Env"
    manager.build_venv(venv_path, with_pip=True)
    venv = VirtualEnv(venv_path)

    default_executable = expected_executable = f"python{'.exe' if WINDOWS else ''}"
    default_pip_executable = expected_pip_executable = f"pip{'.exe' if WINDOWS else ''}"
    major_executable = f"python{sys.version_info[0]}{'.exe' if WINDOWS else ''}"
    major_pip_executable = f"pip{sys.version_info[0]}{'.exe' if WINDOWS else ''}"

    if (
        venv._bin_dir.joinpath(default_executable).exists()
        and venv._bin_dir.joinpath(major_executable).exists()
    ):
        venv._bin_dir.joinpath(default_executable).unlink()
        expected_executable = major_executable

    if (
        venv._bin_dir.joinpath(default_pip_executable).exists()
        and venv._bin_dir.joinpath(major_pip_executable).exists()
    ):
        venv._bin_dir.joinpath(default_pip_executable).unlink()
        expected_pip_executable = major_pip_executable

    venv = VirtualEnv(venv_path)

    assert Path(venv.python).name == expected_executable
    assert Path(venv.pip).name.startswith(expected_pip_executable.split(".")[0])


def test_env_finds_the_correct_executables_for_generic_env(
    tmp_path: Path, manager: EnvManager
) -> None:
    venv_path = tmp_path / "Virtual Env"
    child_venv_path = tmp_path / "Child Virtual Env"
    manager.build_venv(venv_path, with_pip=True)
    parent_venv = VirtualEnv(venv_path)
    manager.build_venv(child_venv_path, executable=parent_venv.python, with_pip=True)
    venv = GenericEnv(parent_venv.path, child_env=VirtualEnv(child_venv_path))

    expected_executable = (
        f"python{sys.version_info[0]}.{sys.version_info[1]}{'.exe' if WINDOWS else ''}"
    )
    expected_pip_executable = (
        f"pip{sys.version_info[0]}.{sys.version_info[1]}{'.exe' if WINDOWS else ''}"
    )

    if WINDOWS:
        expected_executable = "python.exe"
        expected_pip_executable = "pip.exe"

    assert Path(venv.python).name == expected_executable
    assert Path(venv.pip).name == expected_pip_executable


def test_env_finds_fallback_executables_for_generic_env(
    tmp_path: Path, manager: EnvManager
) -> None:
    venv_path = tmp_path / "Virtual Env"
    child_venv_path = tmp_path / "Child Virtual Env"
    manager.build_venv(venv_path, with_pip=True)
    parent_venv = VirtualEnv(venv_path)
    manager.build_venv(child_venv_path, executable=parent_venv.python, with_pip=True)
    venv = GenericEnv(parent_venv.path, child_env=VirtualEnv(child_venv_path))

    default_executable = f"python{'.exe' if WINDOWS else ''}"
    major_executable = f"python{sys.version_info[0]}{'.exe' if WINDOWS else ''}"
    minor_executable = (
        f"python{sys.version_info[0]}.{sys.version_info[1]}{'.exe' if WINDOWS else ''}"
    )
    expected_executable = minor_executable
    if (
        venv._bin_dir.joinpath(expected_executable).exists()
        and venv._bin_dir.joinpath(major_executable).exists()
    ):
        venv._bin_dir.joinpath(expected_executable).unlink()
        expected_executable = major_executable

    if (
        venv._bin_dir.joinpath(expected_executable).exists()
        and venv._bin_dir.joinpath(default_executable).exists()
    ):
        venv._bin_dir.joinpath(expected_executable).unlink()
        expected_executable = default_executable

    default_pip_executable = f"pip{'.exe' if WINDOWS else ''}"
    major_pip_executable = f"pip{sys.version_info[0]}{'.exe' if WINDOWS else ''}"
    minor_pip_executable = (
        f"pip{sys.version_info[0]}.{sys.version_info[1]}{'.exe' if WINDOWS else ''}"
    )
    expected_pip_executable = minor_pip_executable
    if (
        venv._bin_dir.joinpath(expected_pip_executable).exists()
        and venv._bin_dir.joinpath(major_pip_executable).exists()
    ):
        venv._bin_dir.joinpath(expected_pip_executable).unlink()
        expected_pip_executable = major_pip_executable

    if (
        venv._bin_dir.joinpath(expected_pip_executable).exists()
        and venv._bin_dir.joinpath(default_pip_executable).exists()
    ):
        venv._bin_dir.joinpath(expected_pip_executable).unlink()
        expected_pip_executable = default_pip_executable

    if not venv._bin_dir.joinpath(expected_executable).exists():
        expected_executable = default_executable

    if not venv._bin_dir.joinpath(expected_pip_executable).exists():
        expected_pip_executable = default_pip_executable

    venv = GenericEnv(parent_venv.path, child_env=VirtualEnv(child_venv_path))

    assert Path(venv.python).name == expected_executable
    assert Path(venv.pip).name == expected_pip_executable


@pytest.fixture
def extended_without_setup_poetry(
    fixture_dir: FixtureDirGetter, set_project_context: SetProjectContext
) -> Iterator[Poetry]:
    with set_project_context("extended_project_without_setup") as cwd:
        yield Factory().create_poetry(cwd)


def test_build_environment_called_build_script_specified(
    mocker: MockerFixture,
    extended_without_setup_poetry: Poetry,
) -> None:
    patched_install = mocker.patch("poetry.utils.isolated_build.IsolatedEnv.install")

    with ephemeral_environment() as project_env:
        import poetry.utils.env

        spy = mocker.spy(poetry.utils.env, "ephemeral_environment")

        with build_environment(extended_without_setup_poetry, project_env):
            assert patched_install.call_count == 1
            assert patched_install.call_args == mocker.call(["poetry-core", "cython"])

        assert spy.call_count == 1


def test_build_environment_not_called_without_build_script_specified(
    mocker: MockerFixture, poetry: Poetry, tmp_path: Path
) -> None:
    project_env = MockEnv(path=tmp_path / "project")
    ephemeral_env = MockEnv(path=tmp_path / "ephemeral")

    mocker.patch(
        "poetry.utils.env.ephemeral_environment"
    ).return_value.__enter__.return_value = ephemeral_env

    with build_environment(poetry, project_env) as env:
        assert env == project_env
        assert not env.executed  # type: ignore[attr-defined]


def test_command_from_bin_preserves_relative_path(manager: EnvManager) -> None:
    # https://github.com/python-poetry/poetry/issues/7959
    env = manager.get()
    command = env.get_command_from_bin("./foo.py")
    assert command == ["./foo.py"]


@pytest.fixture
def system_env_read_only(system_env: SystemEnv, mocker: MockerFixture) -> SystemEnv:
    original_is_dir_writable = is_dir_writable

    read_only_paths = {system_env.paths[key] for key in SCHEME_NAMES}

    def mock_is_dir_writable(path: Path, create: bool = False) -> bool:
        if str(path) in read_only_paths:
            return False
        return original_is_dir_writable(path, create)

    mocker.patch("poetry.utils.env.base_env.is_dir_writable", new=mock_is_dir_writable)

    return system_env


def test_env_scheme_dict_returns_original_when_writable(system_env: SystemEnv) -> None:
    assert not DeepDiff(system_env.scheme_dict, system_env.paths, ignore_order=True)


def test_env_scheme_dict_returns_modified_when_read_only(
    system_env_read_only: SystemEnv,
) -> None:
    scheme_dict = system_env_read_only.scheme_dict
    assert DeepDiff(scheme_dict, system_env_read_only.paths, ignore_order=True)

    paths = system_env_read_only.paths
    assert all(
        Path(scheme_dict[scheme]).exists()
        and scheme_dict[scheme].startswith(paths["userbase"])
        for scheme in SCHEME_NAMES
    )
