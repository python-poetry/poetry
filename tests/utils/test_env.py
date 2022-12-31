from __future__ import annotations

import os
import subprocess
import sys

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest
import tomlkit

from poetry.core.constraints.version import Version
from poetry.core.toml.file import TOMLFile

from poetry.factory import Factory
from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils._compat import WINDOWS
from poetry.utils.env import GET_BASE_PREFIX
from poetry.utils.env import EnvCommandError
from poetry.utils.env import EnvManager
from poetry.utils.env import GenericEnv
from poetry.utils.env import IncorrectEnvError
from poetry.utils.env import InvalidCurrentPythonVersionError
from poetry.utils.env import MockEnv
from poetry.utils.env import NoCompatiblePythonVersionFound
from poetry.utils.env import SystemEnv
from poetry.utils.env import VirtualEnv
from poetry.utils.env import build_environment
from poetry.utils.helpers import remove_directory


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterator

    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry
    from tests.conftest import Config
    from tests.types import ProjectFactory

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
    def sys_path(self) -> list[str] | None:
        if self._sys_path is not None:
            return self._sys_path

        return super().sys_path


@pytest.fixture()
def poetry(project_factory: ProjectFactory) -> Poetry:
    fixture = Path(__file__).parent.parent / "fixtures" / "simple_project"
    return project_factory("simple", source=fixture)


@pytest.fixture()
def manager(poetry: Poetry) -> EnvManager:
    return EnvManager(poetry)


def test_virtualenvs_with_spaces_in_their_path_work_as_expected(
    tmp_dir: str, manager: EnvManager
):
    venv_path = Path(tmp_dir) / "Virtual Env"

    manager.build_venv(str(venv_path))

    venv = VirtualEnv(venv_path)

    assert venv.run("python", "-V", shell=True).startswith("Python")


@pytest.mark.skipif(sys.platform != "darwin", reason="requires darwin")
def test_venv_backup_exclusion(tmp_dir: str, manager: EnvManager):
    import xattr

    venv_path = Path(tmp_dir) / "Virtual Env"

    manager.build_venv(str(venv_path))

    value = (
        b"bplist00_\x10\x11com.apple.backupd"
        b"\x08\x00\x00\x00\x00\x00\x00\x01\x01\x00\x00\x00\x00\x00\x00\x00"
        b"\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1c"
    )
    assert (
        xattr.getxattr(
            str(venv_path), "com.apple.metadata:com_apple_backup_excludeItem"
        )
        == value
    )


def test_env_commands_with_spaces_in_their_arg_work_as_expected(
    tmp_dir: str, manager: EnvManager
):
    venv_path = Path(tmp_dir) / "Virtual Env"
    manager.build_venv(str(venv_path))
    venv = VirtualEnv(venv_path)
    assert venv.run("python", venv.pip, "--version", shell=True).startswith(
        f"pip {venv.pip_version} from "
    )


def test_env_shell_commands_with_stdinput_in_their_arg_work_as_expected(
    tmp_dir: str, manager: EnvManager
):
    venv_path = Path(tmp_dir) / "Virtual Env"
    manager.build_venv(str(venv_path))
    venv = VirtualEnv(venv_path)
    run_output_path = Path(
        venv.run("python", "-", input_=GET_BASE_PREFIX, shell=True).strip()
    )
    venv_base_prefix_path = Path(str(venv.get_base_prefix()))
    assert run_output_path.resolve() == venv_base_prefix_path.resolve()


def test_env_get_supported_tags_matches_inside_virtualenv(
    tmp_dir: str, manager: EnvManager
):
    venv_path = Path(tmp_dir) / "Virtual Env"
    manager.build_venv(str(venv_path))
    venv = VirtualEnv(venv_path)

    import packaging.tags

    assert venv.get_supported_tags() == list(packaging.tags.sys_tags())


@pytest.fixture
def in_project_venv_dir(poetry: Poetry) -> Iterator[Path]:
    os.environ.pop("VIRTUAL_ENV", None)
    venv_dir = poetry.file.parent.joinpath(".venv")
    venv_dir.mkdir()
    try:
        yield venv_dir
    finally:
        venv_dir.rmdir()


@pytest.mark.parametrize("in_project", [True, False, None])
def test_env_get_venv_with_venv_folder_present(
    manager: EnvManager,
    poetry: Poetry,
    in_project_venv_dir: Path,
    in_project: bool | None,
):
    poetry.config.config["virtualenvs"]["in-project"] = in_project
    venv = manager.get()
    if in_project is False:
        assert venv.path != in_project_venv_dir
    else:
        assert venv.path == in_project_venv_dir


def build_venv(path: Path | str, **__: Any) -> None:
    os.mkdir(str(path))


VERSION_3_7_1 = Version.parse("3.7.1")


def check_output_wrapper(
    version: Version = VERSION_3_7_1,
) -> Callable[[str, Any, Any], str]:
    def check_output(cmd: str, *args: Any, **kwargs: Any) -> str:
        if "sys.version_info[:3]" in cmd:
            return version.text
        elif "sys.version_info[:2]" in cmd:
            return f"{version.major}.{version.minor}"
        elif '-c "import sys; print(sys.executable)"' in cmd:
            return f"/usr/bin/{cmd.split()[0]}"
        else:
            return str(Path("/prefix"))

    return check_output


def test_activate_activates_non_existing_virtualenv_no_envs_file(
    tmp_dir: str,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(),
    )
    mocker.patch(
        "subprocess.Popen.communicate",
        side_effect=[("/prefix", None), ("/prefix", None)],
    )
    m = mocker.patch("poetry.utils.env.EnvManager.build_venv", side_effect=build_venv)

    env = manager.activate("python3.7")

    m.assert_called_with(
        Path(tmp_dir) / f"{venv_name}-py3.7",
        executable="/usr/bin/python3.7",
        flags={
            "always-copy": False,
            "system-site-packages": False,
            "no-pip": False,
            "no-setuptools": False,
        },
        prompt="simple-project-py3.7",
    )

    envs_file = TOMLFile(Path(tmp_dir) / "envs.toml")
    assert envs_file.exists()
    envs = envs_file.read()
    assert envs[venv_name]["minor"] == "3.7"
    assert envs[venv_name]["patch"] == "3.7.1"

    assert env.path == Path(tmp_dir) / f"{venv_name}-py3.7"
    assert env.base == Path("/prefix")


def test_activate_activates_existing_virtualenv_no_envs_file(
    tmp_dir: str,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    os.mkdir(os.path.join(tmp_dir, f"{venv_name}-py3.7"))

    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(),
    )
    mocker.patch(
        "subprocess.Popen.communicate",
        side_effect=[("/prefix", None)],
    )
    m = mocker.patch("poetry.utils.env.EnvManager.build_venv", side_effect=build_venv)

    env = manager.activate("python3.7")

    m.assert_not_called()

    envs_file = TOMLFile(Path(tmp_dir) / "envs.toml")
    assert envs_file.exists()
    envs = envs_file.read()
    assert envs[venv_name]["minor"] == "3.7"
    assert envs[venv_name]["patch"] == "3.7.1"

    assert env.path == Path(tmp_dir) / f"{venv_name}-py3.7"
    assert env.base == Path("/prefix")


def test_activate_activates_same_virtualenv_with_envs_file(
    tmp_dir: str,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    envs_file = TOMLFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.1"}
    envs_file.write(doc)

    os.mkdir(os.path.join(tmp_dir, f"{venv_name}-py3.7"))

    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(),
    )
    mocker.patch(
        "subprocess.Popen.communicate",
        side_effect=[("/prefix", None)],
    )
    m = mocker.patch("poetry.utils.env.EnvManager.create_venv")

    env = manager.activate("python3.7")

    m.assert_not_called()

    assert envs_file.exists()
    envs = envs_file.read()
    assert envs[venv_name]["minor"] == "3.7"
    assert envs[venv_name]["patch"] == "3.7.1"

    assert env.path == Path(tmp_dir) / f"{venv_name}-py3.7"
    assert env.base == Path("/prefix")


def test_activate_activates_different_virtualenv_with_envs_file(
    tmp_dir: str,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    envs_file = TOMLFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.1"}
    envs_file.write(doc)

    os.mkdir(os.path.join(tmp_dir, f"{venv_name}-py3.7"))

    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )
    mocker.patch(
        "subprocess.Popen.communicate",
        side_effect=[("/prefix", None), ("/prefix", None), ("/prefix", None)],
    )
    m = mocker.patch("poetry.utils.env.EnvManager.build_venv", side_effect=build_venv)

    env = manager.activate("python3.6")

    m.assert_called_with(
        Path(tmp_dir) / f"{venv_name}-py3.6",
        executable="/usr/bin/python3.6",
        flags={
            "always-copy": False,
            "system-site-packages": False,
            "no-pip": False,
            "no-setuptools": False,
        },
        prompt="simple-project-py3.6",
    )

    assert envs_file.exists()
    envs = envs_file.read()
    assert envs[venv_name]["minor"] == "3.6"
    assert envs[venv_name]["patch"] == "3.6.6"

    assert env.path == Path(tmp_dir) / f"{venv_name}-py3.6"
    assert env.base == Path("/prefix")


def test_activate_activates_recreates_for_different_patch(
    tmp_dir: str,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    envs_file = TOMLFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.0"}
    envs_file.write(doc)

    os.mkdir(os.path.join(tmp_dir, f"{venv_name}-py3.7"))

    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(),
    )
    mocker.patch(
        "subprocess.Popen.communicate",
        side_effect=[
            ("/prefix", None),
            ('{"version_info": [3, 7, 0]}', None),
            ("/prefix", None),
            ("/prefix", None),
            ("/prefix", None),
        ],
    )
    build_venv_m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=build_venv
    )
    remove_venv_m = mocker.patch(
        "poetry.utils.env.EnvManager.remove_venv", side_effect=EnvManager.remove_venv
    )

    env = manager.activate("python3.7")

    build_venv_m.assert_called_with(
        Path(tmp_dir) / f"{venv_name}-py3.7",
        executable="/usr/bin/python3.7",
        flags={
            "always-copy": False,
            "system-site-packages": False,
            "no-pip": False,
            "no-setuptools": False,
        },
        prompt="simple-project-py3.7",
    )
    remove_venv_m.assert_called_with(Path(tmp_dir) / f"{venv_name}-py3.7")

    assert envs_file.exists()
    envs = envs_file.read()
    assert envs[venv_name]["minor"] == "3.7"
    assert envs[venv_name]["patch"] == "3.7.1"

    assert env.path == Path(tmp_dir) / f"{venv_name}-py3.7"
    assert env.base == Path("/prefix")
    assert (Path(tmp_dir) / f"{venv_name}-py3.7").exists()


def test_activate_does_not_recreate_when_switching_minor(
    tmp_dir: str,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    envs_file = TOMLFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.0"}
    envs_file.write(doc)

    os.mkdir(os.path.join(tmp_dir, f"{venv_name}-py3.7"))
    os.mkdir(os.path.join(tmp_dir, f"{venv_name}-py3.6"))

    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )
    mocker.patch(
        "subprocess.Popen.communicate",
        side_effect=[("/prefix", None), ("/prefix", None), ("/prefix", None)],
    )
    build_venv_m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=build_venv
    )
    remove_venv_m = mocker.patch(
        "poetry.utils.env.EnvManager.remove_venv", side_effect=EnvManager.remove_venv
    )

    env = manager.activate("python3.6")

    build_venv_m.assert_not_called()
    remove_venv_m.assert_not_called()

    assert envs_file.exists()
    envs = envs_file.read()
    assert envs[venv_name]["minor"] == "3.6"
    assert envs[venv_name]["patch"] == "3.6.6"

    assert env.path == Path(tmp_dir) / f"{venv_name}-py3.6"
    assert env.base == Path("/prefix")
    assert (Path(tmp_dir) / f"{venv_name}-py3.6").exists()


def test_deactivate_non_activated_but_existing(
    tmp_dir: str,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    python = ".".join(str(c) for c in sys.version_info[:2])
    (Path(tmp_dir) / f"{venv_name}-py{python}").mkdir()

    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(),
    )

    manager.deactivate()
    env = manager.get()

    assert env.path == Path(tmp_dir) / f"{venv_name}-py{python}"
    assert Path("/prefix")


def test_deactivate_activated(
    tmp_dir: str,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    version = Version.from_parts(*sys.version_info[:3])
    other_version = Version.parse("3.4") if version.major == 2 else version.next_minor()
    (Path(tmp_dir) / f"{venv_name}-py{version.major}.{version.minor}").mkdir()
    (
        Path(tmp_dir) / f"{venv_name}-py{other_version.major}.{other_version.minor}"
    ).mkdir()

    envs_file = TOMLFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {
        "minor": f"{other_version.major}.{other_version.minor}",
        "patch": other_version.text,
    }
    envs_file.write(doc)

    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(),
    )

    manager.deactivate()
    env = manager.get()

    assert env.path == Path(tmp_dir) / f"{venv_name}-py{version.major}.{version.minor}"
    assert Path("/prefix")

    envs = envs_file.read()
    assert len(envs) == 0


def test_get_prefers_explicitly_activated_virtualenvs_over_env_var(
    tmp_dir: str,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
):
    os.environ["VIRTUAL_ENV"] = "/environment/prefix"

    config.merge({"virtualenvs": {"path": str(tmp_dir)}})
    (Path(tmp_dir) / f"{venv_name}-py3.7").mkdir()

    envs_file = TOMLFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.0"}
    envs_file.write(doc)

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(),
    )
    mocker.patch(
        "subprocess.Popen.communicate",
        side_effect=[("/prefix", None)],
    )

    env = manager.get()

    assert env.path == Path(tmp_dir) / f"{venv_name}-py3.7"
    assert env.base == Path("/prefix")


def test_list(
    tmp_dir: str,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    venv_name: str,
):
    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    (Path(tmp_dir) / f"{venv_name}-py3.7").mkdir()
    (Path(tmp_dir) / f"{venv_name}-py3.6").mkdir()

    venvs = manager.list()

    assert len(venvs) == 2
    assert venvs[0].path == (Path(tmp_dir) / f"{venv_name}-py3.6")
    assert venvs[1].path == (Path(tmp_dir) / f"{venv_name}-py3.7")


def test_remove_by_python_version(
    tmp_dir: str,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
):
    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    (Path(tmp_dir) / f"{venv_name}-py3.7").mkdir()
    (Path(tmp_dir) / f"{venv_name}-py3.6").mkdir()

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )

    venv = manager.remove("3.6")

    expected_venv_path = Path(tmp_dir) / f"{venv_name}-py3.6"
    assert venv.path == expected_venv_path
    assert not expected_venv_path.exists()


def test_remove_by_name(
    tmp_dir: str,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
):
    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    (Path(tmp_dir) / f"{venv_name}-py3.7").mkdir()
    (Path(tmp_dir) / f"{venv_name}-py3.6").mkdir()

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )

    venv = manager.remove(f"{venv_name}-py3.6")

    expected_venv_path = Path(tmp_dir) / f"{venv_name}-py3.6"
    assert venv.path == expected_venv_path
    assert not expected_venv_path.exists()


def test_remove_by_string_with_python_and_version(
    tmp_dir: str,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
):
    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    (Path(tmp_dir) / f"{venv_name}-py3.7").mkdir()
    (Path(tmp_dir) / f"{venv_name}-py3.6").mkdir()

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )

    venv = manager.remove("python3.6")

    expected_venv_path = Path(tmp_dir) / f"{venv_name}-py3.6"
    assert venv.path == expected_venv_path
    assert not expected_venv_path.exists()


def test_remove_by_full_path_to_python(
    tmp_dir: str,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
):
    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    (Path(tmp_dir) / f"{venv_name}-py3.7").mkdir()
    (Path(tmp_dir) / f"{venv_name}-py3.6").mkdir()

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )

    expected_venv_path = Path(tmp_dir) / f"{venv_name}-py3.6"
    python_path = expected_venv_path / "bin" / "python"

    venv = manager.remove(str(python_path))

    assert venv.path == expected_venv_path
    assert not expected_venv_path.exists()


def test_raises_if_acting_on_different_project_by_full_path(
    tmp_dir: str,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
):
    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    different_venv_name = "different-project"
    different_venv_path = Path(tmp_dir) / f"{different_venv_name}-py3.6"
    different_venv_bin_path = different_venv_path / "bin"
    different_venv_bin_path.mkdir(parents=True)

    python_path = different_venv_bin_path / "python"
    python_path.touch(exist_ok=True)

    # Patch initial call where python env path is extracted
    mocker.patch(
        "subprocess.check_output",
        side_effect=lambda *args, **kwargs: str(different_venv_path),
    )

    with pytest.raises(IncorrectEnvError):
        manager.remove(str(python_path))


def test_raises_if_acting_on_different_project_by_name(
    tmp_dir: str,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
):
    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    different_venv_name = (
        EnvManager.generate_env_name(
            "different-project",
            str(poetry.file.parent),
        )
        + "-py3.6"
    )
    different_venv_path = Path(tmp_dir) / different_venv_name
    different_venv_bin_path = different_venv_path / "bin"
    different_venv_bin_path.mkdir(parents=True)

    python_path = different_venv_bin_path / "python"
    python_path.touch(exist_ok=True)

    with pytest.raises(IncorrectEnvError):
        manager.remove(different_venv_name)


def test_raises_when_passing_old_env_after_dir_rename(
    tmp_dir: str,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    venv_name: str,
):
    # Make sure that poetry raises when trying to remove old venv after you've renamed
    # root directory of the project, which will create another venv with new name.
    # This is not ideal as you still "can't" remove it by name, but it at least doesn't
    # cause any unwanted side effects
    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    previous_venv_name = EnvManager.generate_env_name(
        poetry.package.name,
        "previous_dir_name",
    )
    venv_path = Path(tmp_dir) / f"{venv_name}-py3.6"
    venv_path.mkdir()

    previous_venv_name = f"{previous_venv_name}-py3.6"
    previous_venv_path = Path(tmp_dir) / previous_venv_name
    previous_venv_path.mkdir()

    with pytest.raises(IncorrectEnvError):
        manager.remove(previous_venv_name)


def test_remove_also_deactivates(
    tmp_dir: str,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
):
    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    (Path(tmp_dir) / f"{venv_name}-py3.7").mkdir()
    (Path(tmp_dir) / f"{venv_name}-py3.6").mkdir()

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )

    envs_file = TOMLFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.6", "patch": "3.6.6"}
    envs_file.write(doc)

    venv = manager.remove("python3.6")

    expected_venv_path = Path(tmp_dir) / f"{venv_name}-py3.6"
    assert venv.path == expected_venv_path
    assert not expected_venv_path.exists()

    envs = envs_file.read()
    assert venv_name not in envs


def test_remove_keeps_dir_if_not_deleteable(
    tmp_dir: str,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
):
    # Ensure we empty rather than delete folder if its is an active mount point.
    # See https://github.com/python-poetry/poetry/pull/2064
    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    venv_path = Path(tmp_dir) / f"{venv_name}-py3.6"
    venv_path.mkdir()

    folder1_path = venv_path / "folder1"
    folder1_path.mkdir()

    file1_path = folder1_path / "file1"
    file1_path.touch(exist_ok=False)

    file2_path = venv_path / "file2"
    file2_path.touch(exist_ok=False)

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )

    def err_on_rm_venv_only(path: Path | str, *args: Any, **kwargs: Any) -> None:
        if str(path) == str(venv_path):
            raise OSError(16, "Test error")  # ERRNO 16: Device or resource busy
        else:
            remove_directory(path)

    m = mocker.patch(
        "poetry.utils.env.remove_directory", side_effect=err_on_rm_venv_only
    )

    venv = manager.remove(f"{venv_name}-py3.6")

    m.assert_any_call(venv_path)

    assert venv_path == venv.path
    assert venv_path.exists()

    assert not folder1_path.exists()
    assert not file1_path.exists()
    assert not file2_path.exists()

    m.side_effect = remove_directory  # Avoid teardown using `err_on_rm_venv_only`


@pytest.mark.skipif(os.name == "nt", reason="Symlinks are not support for Windows")
def test_env_has_symlinks_on_nix(tmp_dir: str, tmp_venv: VirtualEnv):
    assert os.path.islink(tmp_venv.python)


def test_run_with_input(tmp_dir: str, tmp_venv: VirtualEnv):
    result = tmp_venv.run("python", "-", input_=MINIMAL_SCRIPT)

    assert result == "Minimal Output" + os.linesep


def test_run_with_input_non_zero_return(tmp_dir: str, tmp_venv: VirtualEnv):
    with pytest.raises(EnvCommandError) as process_error:
        # Test command that will return non-zero returncode.
        tmp_venv.run("python", "-", input_=ERRORING_SCRIPT)

    assert process_error.value.e.returncode == 1


def test_run_with_keyboard_interrupt(
    tmp_dir: str, tmp_venv: VirtualEnv, mocker: MockerFixture
):
    mocker.patch("subprocess.run", side_effect=KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        tmp_venv.run("python", "-", input_=MINIMAL_SCRIPT)
    subprocess.run.assert_called_once()


def test_call_with_input_and_keyboard_interrupt(
    tmp_dir: str, tmp_venv: VirtualEnv, mocker: MockerFixture
):
    mocker.patch("subprocess.run", side_effect=KeyboardInterrupt())
    kwargs = {"call": True}
    with pytest.raises(KeyboardInterrupt):
        tmp_venv.run("python", "-", input_=MINIMAL_SCRIPT, **kwargs)
    subprocess.run.assert_called_once()


def test_call_no_input_with_keyboard_interrupt(
    tmp_dir: str, tmp_venv: VirtualEnv, mocker: MockerFixture
):
    mocker.patch("subprocess.call", side_effect=KeyboardInterrupt())
    kwargs = {"call": True}
    with pytest.raises(KeyboardInterrupt):
        tmp_venv.run("python", "-", **kwargs)
    subprocess.call.assert_called_once()


def test_run_with_called_process_error(
    tmp_dir: str, tmp_venv: VirtualEnv, mocker: MockerFixture
):
    mocker.patch(
        "subprocess.run", side_effect=subprocess.CalledProcessError(42, "some_command")
    )
    with pytest.raises(EnvCommandError):
        tmp_venv.run("python", "-", input_=MINIMAL_SCRIPT)
    subprocess.run.assert_called_once()


def test_call_with_input_and_called_process_error(
    tmp_dir: str, tmp_venv: VirtualEnv, mocker: MockerFixture
):
    mocker.patch(
        "subprocess.run", side_effect=subprocess.CalledProcessError(42, "some_command")
    )
    kwargs = {"call": True}
    with pytest.raises(EnvCommandError):
        tmp_venv.run("python", "-", input_=MINIMAL_SCRIPT, **kwargs)
    subprocess.run.assert_called_once()


def test_call_no_input_with_called_process_error(
    tmp_dir: str, tmp_venv: VirtualEnv, mocker: MockerFixture
):
    mocker.patch(
        "subprocess.call", side_effect=subprocess.CalledProcessError(42, "some_command")
    )
    kwargs = {"call": True}
    with pytest.raises(EnvCommandError):
        tmp_venv.run("python", "-", **kwargs)
    subprocess.call.assert_called_once()


def test_create_venv_tries_to_find_a_compatible_python_executable_using_generic_ones_first(  # noqa: E501
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    config_virtualenvs_path: Path,
    venv_name: str,
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    poetry.package.python_versions = "^3.6"

    mocker.patch("sys.version_info", (2, 7, 16))
    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.7.5")),
    )
    m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=lambda *args, **kwargs: ""
    )

    manager.create_venv()

    m.assert_called_with(
        config_virtualenvs_path / f"{venv_name}-py3.7",
        executable="python3",
        flags={
            "always-copy": False,
            "system-site-packages": False,
            "no-pip": False,
            "no-setuptools": False,
        },
        prompt="simple-project-py3.7",
    )


def test_create_venv_tries_to_find_a_compatible_python_executable_using_specific_ones(
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    config_virtualenvs_path: Path,
    venv_name: str,
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    poetry.package.python_versions = "^3.6"

    mocker.patch("sys.version_info", (2, 7, 16))
    mocker.patch("subprocess.check_output", side_effect=["3.5.3", "3.9.0"])
    m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=lambda *args, **kwargs: ""
    )

    manager.create_venv()

    m.assert_called_with(
        config_virtualenvs_path / f"{venv_name}-py3.9",
        executable="python3.9",
        flags={
            "always-copy": False,
            "system-site-packages": False,
            "no-pip": False,
            "no-setuptools": False,
        },
        prompt="simple-project-py3.9",
    )


def test_create_venv_fails_if_no_compatible_python_version_could_be_found(
    manager: EnvManager, poetry: Poetry, config: Config, mocker: MockerFixture
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    poetry.package.python_versions = "^4.8"

    mocker.patch("subprocess.check_output", side_effect=["", "", "", ""])
    m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=lambda *args, **kwargs: ""
    )

    with pytest.raises(NoCompatiblePythonVersionFound) as e:
        manager.create_venv()

    expected_message = (
        "Poetry was unable to find a compatible version. "
        "If you have one, you can explicitly use it "
        'via the "env use" command.'
    )

    assert str(e.value) == expected_message
    assert m.call_count == 0


def test_create_venv_does_not_try_to_find_compatible_versions_with_executable(
    manager: EnvManager, poetry: Poetry, config: Config, mocker: MockerFixture
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    poetry.package.python_versions = "^4.8"

    mocker.patch("subprocess.check_output", side_effect=["3.8.0"])
    m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=lambda *args, **kwargs: ""
    )

    with pytest.raises(NoCompatiblePythonVersionFound) as e:
        manager.create_venv(executable="3.8")

    expected_message = (
        "The specified Python version (3.8.0) is not supported by the project (^4.8).\n"
        "Please choose a compatible version or loosen the python constraint "
        "specified in the pyproject.toml file."
    )

    assert str(e.value) == expected_message
    assert m.call_count == 0


def test_create_venv_uses_patch_version_to_detect_compatibility(
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    config_virtualenvs_path: Path,
    venv_name: str,
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    version = Version.from_parts(*sys.version_info[:3])
    poetry.package.python_versions = "^" + ".".join(
        str(c) for c in sys.version_info[:3]
    )

    mocker.patch("sys.version_info", (version.major, version.minor, version.patch + 1))
    check_output = mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.9")),
    )
    m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=lambda *args, **kwargs: ""
    )

    manager.create_venv()

    assert not check_output.called
    m.assert_called_with(
        config_virtualenvs_path / f"{venv_name}-py{version.major}.{version.minor}",
        executable=None,
        flags={
            "always-copy": False,
            "system-site-packages": False,
            "no-pip": False,
            "no-setuptools": False,
        },
        prompt=f"simple-project-py{version.major}.{version.minor}",
    )


def test_create_venv_uses_patch_version_to_detect_compatibility_with_executable(
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    config_virtualenvs_path: Path,
    venv_name: str,
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    version = Version.from_parts(*sys.version_info[:3])
    poetry.package.python_versions = f"~{version.major}.{version.minor-1}.0"

    check_output = mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(
            Version.parse(f"{version.major}.{version.minor - 1}.0")
        ),
    )
    m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=lambda *args, **kwargs: ""
    )

    manager.create_venv(executable=f"python{version.major}.{version.minor - 1}")

    assert check_output.called
    m.assert_called_with(
        config_virtualenvs_path / f"{venv_name}-py{version.major}.{version.minor - 1}",
        executable=f"python{version.major}.{version.minor - 1}",
        flags={
            "always-copy": False,
            "system-site-packages": False,
            "no-pip": False,
            "no-setuptools": False,
        },
        prompt=f"simple-project-py{version.major}.{version.minor - 1}",
    )


def test_create_venv_fails_if_current_python_version_is_not_supported(
    manager: EnvManager, poetry: Poetry
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    manager.create_venv()

    current_version = Version.parse(".".join(str(c) for c in sys.version_info[:3]))
    next_version = ".".join(
        str(c) for c in (current_version.major, current_version.minor + 1, 0)
    )
    package_version = "~" + next_version
    poetry.package.python_versions = package_version

    with pytest.raises(InvalidCurrentPythonVersionError) as e:
        manager.create_venv()

    expected_message = (
        f"Current Python version ({current_version}) is not allowed by the project"
        f' ({package_version}).\nPlease change python executable via the "env use"'
        " command."
    )

    assert expected_message == str(e.value)


def test_activate_with_in_project_setting_does_not_fail_if_no_venvs_dir(
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    tmp_dir: str,
    mocker: MockerFixture,
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    config.merge(
        {
            "virtualenvs": {
                "path": str(Path(tmp_dir) / "virtualenvs"),
                "in-project": True,
            }
        }
    )

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(),
    )
    mocker.patch(
        "subprocess.Popen.communicate",
        side_effect=[("/prefix", None), ("/prefix", None)],
    )
    m = mocker.patch("poetry.utils.env.EnvManager.build_venv")

    manager.activate("python3.7")

    m.assert_called_with(
        poetry.file.parent / ".venv",
        executable="/usr/bin/python3.7",
        flags={
            "always-copy": False,
            "system-site-packages": False,
            "no-pip": False,
            "no-setuptools": False,
        },
        prompt="simple-project-py3.7",
    )

    envs_file = TOMLFile(Path(tmp_dir) / "virtualenvs" / "envs.toml")
    assert not envs_file.exists()


def test_system_env_has_correct_paths():
    env = SystemEnv(Path(sys.prefix))

    paths = env.paths

    assert paths.get("purelib") is not None
    assert paths.get("platlib") is not None
    assert paths.get("scripts") is not None
    assert env.site_packages.path == Path(paths["purelib"])


@pytest.mark.parametrize(
    "enabled",
    [True, False],
)
def test_system_env_usersite(mocker: MockerFixture, enabled: bool):
    mocker.patch("site.check_enableusersite", return_value=enabled)
    env = SystemEnv(Path(sys.prefix))
    assert (enabled and env.usersite is not None) or (
        not enabled and env.usersite is None
    )


def test_venv_has_correct_paths(tmp_venv: VirtualEnv):
    paths = tmp_venv.paths

    assert paths.get("purelib") is not None
    assert paths.get("platlib") is not None
    assert paths.get("scripts") is not None
    assert tmp_venv.site_packages.path == Path(paths["purelib"])


def test_env_system_packages(tmp_path: Path, poetry: Poetry):
    venv_path = tmp_path / "venv"
    pyvenv_cfg = venv_path / "pyvenv.cfg"

    EnvManager(poetry).build_venv(path=venv_path, flags={"system-site-packages": True})

    assert "include-system-site-packages = true" in pyvenv_cfg.read_text()


@pytest.mark.parametrize(
    ("flags", "packages"),
    [
        ({"no-pip": False}, {"pip", "wheel"}),
        ({"no-pip": False, "no-wheel": True}, {"pip"}),
        ({"no-pip": True}, set()),
        ({"no-setuptools": False}, {"setuptools"}),
        ({"no-setuptools": True}, set()),
        ({"no-pip": True, "no-setuptools": False}, {"setuptools"}),
        ({"no-wheel": False}, {"wheel"}),
        ({}, set()),
    ],
)
def test_env_no_pip(
    tmp_path: Path, poetry: Poetry, flags: dict[str, bool], packages: set[str]
):
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


def test_env_finds_the_correct_executables(tmp_dir: str, manager: EnvManager):
    venv_path = Path(tmp_dir) / "Virtual Env"
    manager.build_venv(str(venv_path), with_pip=True)
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
    tmp_dir: str, manager: EnvManager
):
    venv_path = Path(tmp_dir) / "Virtual Env"
    child_venv_path = Path(tmp_dir) / "Child Virtual Env"
    manager.build_venv(str(venv_path), with_pip=True)
    parent_venv = VirtualEnv(venv_path)
    manager.build_venv(
        str(child_venv_path), executable=parent_venv.python, with_pip=True
    )
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
    tmp_dir: str, manager: EnvManager
):
    venv_path = Path(tmp_dir) / "Virtual Env"
    child_venv_path = Path(tmp_dir) / "Child Virtual Env"
    manager.build_venv(str(venv_path), with_pip=True)
    parent_venv = VirtualEnv(venv_path)
    manager.build_venv(
        str(child_venv_path), executable=parent_venv.python, with_pip=True
    )
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


def test_create_venv_accepts_fallback_version_w_nonzero_patchlevel(
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    config_virtualenvs_path: Path,
    venv_name: str,
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    poetry.package.python_versions = "~3.5.1"

    check_output = mocker.patch(
        "subprocess.check_output",
        side_effect=lambda cmd, *args, **kwargs: str(
            "3.5.12" if "python3.5" in cmd else "3.7.1"
        ),
    )
    m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=lambda *args, **kwargs: ""
    )

    manager.create_venv()

    assert check_output.called
    m.assert_called_with(
        config_virtualenvs_path / f"{venv_name}-py3.5",
        executable="python3.5",
        flags={
            "always-copy": False,
            "system-site-packages": False,
            "no-pip": False,
            "no-setuptools": False,
        },
        prompt="simple-project-py3.5",
    )


def test_generate_env_name_ignores_case_for_case_insensitive_fs(
    poetry: Poetry,
    tmp_dir: str,
):
    venv_name1 = EnvManager.generate_env_name(poetry.package.name, "MyDiR")
    venv_name2 = EnvManager.generate_env_name(poetry.package.name, "mYdIr")
    if sys.platform == "win32":
        assert venv_name1 == venv_name2
    else:
        assert venv_name1 != venv_name2


def test_generate_env_name_uses_real_path(tmp_dir: str, mocker: MockerFixture):
    mocker.patch("os.path.realpath", return_value="the_real_dir")
    venv_name1 = EnvManager.generate_env_name("simple-project", "the_real_dir")
    venv_name2 = EnvManager.generate_env_name("simple-project", "linked_dir")
    assert venv_name1 == venv_name2


@pytest.fixture()
def extended_without_setup_poetry() -> Poetry:
    poetry = Factory().create_poetry(
        Path(__file__).parent.parent / "fixtures" / "extended_project_without_setup"
    )

    return poetry


def test_build_environment_called_build_script_specified(
    mocker: MockerFixture, extended_without_setup_poetry: Poetry, tmp_dir: str
):
    project_env = MockEnv(path=Path(tmp_dir) / "project")
    ephemeral_env = MockEnv(path=Path(tmp_dir) / "ephemeral")

    mocker.patch(
        "poetry.utils.env.ephemeral_environment"
    ).return_value.__enter__.return_value = ephemeral_env

    with build_environment(extended_without_setup_poetry, project_env) as env:
        assert env == ephemeral_env
        assert env.executed == [
            [
                sys.executable,
                env.pip_embedded,
                "install",
                "--disable-pip-version-check",
                "--ignore-installed",
                "--no-input",
                *extended_without_setup_poetry.pyproject.build_system.requires,
            ]
        ]


def test_build_environment_not_called_without_build_script_specified(
    mocker: MockerFixture, poetry: Poetry, tmp_dir: str
):
    project_env = MockEnv(path=Path(tmp_dir) / "project")
    ephemeral_env = MockEnv(path=Path(tmp_dir) / "ephemeral")

    mocker.patch(
        "poetry.utils.env.ephemeral_environment"
    ).return_value.__enter__.return_value = ephemeral_env

    with build_environment(poetry, project_env) as env:
        assert env == project_env
        assert not env.executed


def test_create_venv_project_name_empty_sets_correct_prompt(
    project_factory: ProjectFactory,
    config: Config,
    mocker: MockerFixture,
    config_virtualenvs_path: Path,
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    fixture = Path(__file__).parent.parent / "fixtures" / "no_name_project"
    poetry = project_factory("no", source=fixture)
    manager = EnvManager(poetry)

    poetry.package.python_versions = "^3.7"
    venv_name = manager.generate_env_name("", str(poetry.file.parent))

    mocker.patch("sys.version_info", (2, 7, 16))
    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.7.5")),
    )
    m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=lambda *args, **kwargs: ""
    )

    manager.create_venv()

    m.assert_called_with(
        config_virtualenvs_path / f"{venv_name}-py3.7",
        executable="python3",
        flags={
            "always-copy": False,
            "system-site-packages": False,
            "no-pip": False,
            "no-setuptools": False,
        },
        prompt="virtualenv-py3.7",
    )
