import os
import shutil
import subprocess
import sys

from pathlib import Path
<<<<<<< HEAD
from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from typing import Iterator
from typing import List
from typing import Optional
=======
from typing import Any
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
from typing import Union

import pytest
import tomlkit

from cleo.io.null_io import NullIO
<<<<<<< HEAD
from poetry.core.semver.version import Version
from poetry.core.toml.file import TOMLFile

from poetry.factory import Factory
from poetry.utils._compat import WINDOWS
from poetry.utils.env import GET_BASE_PREFIX
from poetry.utils.env import EnvCommandError
from poetry.utils.env import EnvManager
from poetry.utils.env import GenericEnv
=======

from poetry.core.semver.version import Version
from poetry.core.toml.file import TOMLFile
from poetry.factory import Factory
from poetry.utils.env import GET_BASE_PREFIX
from poetry.utils.env import EnvCommandError
from poetry.utils.env import EnvManager
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
from poetry.utils.env import NoCompatiblePythonVersionFound
from poetry.utils.env import SystemEnv
from poetry.utils.env import VirtualEnv


<<<<<<< HEAD
if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry
    from tests.conftest import Config

=======
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
MINIMAL_SCRIPT = """\

print("Minimal Output"),
"""

# Script expected to fail.
ERRORING_SCRIPT = """\
import nullpackage

print("nullpackage loaded"),
"""


class MockVirtualEnv(VirtualEnv):
<<<<<<< HEAD
    def __init__(
        self,
        path: Path,
        base: Optional[Path] = None,
        sys_path: Optional[List[str]] = None,
    ):
        super().__init__(path, base=base)
=======
    def __init__(self, path, base=None, sys_path=None):
        super(MockVirtualEnv, self).__init__(path, base=base)
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

        self._sys_path = sys_path

    @property
<<<<<<< HEAD
    def sys_path(self) -> Optional[List[str]]:
        if self._sys_path is not None:
            return self._sys_path

        return super().sys_path


@pytest.fixture()
def poetry(config: "Config") -> "Poetry":
=======
    def sys_path(self):
        if self._sys_path is not None:
            return self._sys_path

        return super(MockVirtualEnv, self).sys_path


@pytest.fixture()
def poetry(config):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    poetry = Factory().create_poetry(
        Path(__file__).parent.parent / "fixtures" / "simple_project"
    )
    poetry.set_config(config)

    return poetry


@pytest.fixture()
<<<<<<< HEAD
def manager(poetry: "Poetry") -> EnvManager:
    return EnvManager(poetry)


def test_virtualenvs_with_spaces_in_their_path_work_as_expected(
    tmp_dir: str, manager: EnvManager
):
=======
def manager(poetry):
    return EnvManager(poetry)


def test_virtualenvs_with_spaces_in_their_path_work_as_expected(tmp_dir, manager):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    venv_path = Path(tmp_dir) / "Virtual Env"

    manager.build_venv(str(venv_path))

    venv = VirtualEnv(venv_path)

    assert venv.run("python", "-V", shell=True).startswith("Python")


<<<<<<< HEAD
def test_env_commands_with_spaces_in_their_arg_work_as_expected(
    tmp_dir: str, manager: EnvManager
):
=======
def test_env_commands_with_spaces_in_their_arg_work_as_expected(tmp_dir, manager):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    venv_path = Path(tmp_dir) / "Virtual Env"
    manager.build_venv(str(venv_path))
    venv = VirtualEnv(venv_path)
    assert venv.run("python", venv.pip, "--version", shell=True).startswith(
<<<<<<< HEAD
        f"pip {venv.pip_version} from "
=======
        "pip {} from ".format(venv.pip_version)
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    )


def test_env_shell_commands_with_stdinput_in_their_arg_work_as_expected(
<<<<<<< HEAD
    tmp_dir: str, manager: EnvManager
=======
    tmp_dir, manager
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    venv_path = Path(tmp_dir) / "Virtual Env"
    manager.build_venv(str(venv_path))
    venv = VirtualEnv(venv_path)
<<<<<<< HEAD
    run_output_path = Path(
        venv.run("python", "-", input_=GET_BASE_PREFIX, shell=True).strip()
    )
    venv_base_prefix_path = Path(str(venv.get_base_prefix()))
    assert run_output_path.resolve() == venv_base_prefix_path.resolve()


@pytest.fixture
def in_project_venv_dir(poetry: "Poetry") -> Iterator[Path]:
=======
    assert venv.run("python", "-", input_=GET_BASE_PREFIX, shell=True).strip() == str(
        venv.get_base_prefix()
    )


@pytest.fixture
def in_project_venv_dir(poetry):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    os.environ.pop("VIRTUAL_ENV", None)
    venv_dir = poetry.file.parent.joinpath(".venv")
    venv_dir.mkdir()
    try:
        yield venv_dir
    finally:
        venv_dir.rmdir()


@pytest.mark.parametrize("in_project", [True, False, None])
def test_env_get_venv_with_venv_folder_present(
<<<<<<< HEAD
    manager: EnvManager,
    poetry: "Poetry",
    in_project_venv_dir: Path,
    in_project: Optional[bool],
=======
    manager, poetry, in_project_venv_dir, in_project
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    poetry.config.config["virtualenvs"]["in-project"] = in_project
    venv = manager.get()
    if in_project is False:
        assert venv.path != in_project_venv_dir
    else:
        assert venv.path == in_project_venv_dir


<<<<<<< HEAD
def build_venv(path: Union[Path, str], **__: Any) -> None:
    os.mkdir(str(path))


VERSION_3_7_1 = Version.parse("3.7.1")


def check_output_wrapper(
    version: Version = VERSION_3_7_1,
) -> Callable[[List[str], Any, Any], str]:
    def check_output(cmd: List[str], *args: Any, **kwargs: Any) -> str:
        if "sys.version_info[:3]" in cmd:
            return version.text
        elif "sys.version_info[:2]" in cmd:
            return f"{version.major}.{version.minor}"
=======
def build_venv(path: Union[Path, str], **__: Any) -> ():
    os.mkdir(str(path))


def check_output_wrapper(version=Version.parse("3.7.1")):
    def check_output(cmd, *args, **kwargs):
        if "sys.version_info[:3]" in cmd:
            return version.text
        elif "sys.version_info[:2]" in cmd:
            return "{}.{}".format(version.major, version.minor)
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        else:
            return str(Path("/prefix"))

    return check_output


def test_activate_activates_non_existing_virtualenv_no_envs_file(
<<<<<<< HEAD
    tmp_dir: str,
    manager: EnvManager,
    poetry: "Poetry",
    config: "Config",
    mocker: "MockerFixture",
=======
    tmp_dir, manager, poetry, config, mocker
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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

    env = manager.activate("python3.7", NullIO())
    venv_name = EnvManager.generate_env_name("simple-project", str(poetry.file.parent))

    m.assert_called_with(
<<<<<<< HEAD
        Path(tmp_dir) / f"{venv_name}-py3.7",
=======
        Path(tmp_dir) / "{}-py3.7".format(venv_name),
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        executable="python3.7",
        flags={"always-copy": False, "system-site-packages": False},
        with_pip=True,
        with_setuptools=True,
        with_wheel=True,
    )

    envs_file = TOMLFile(Path(tmp_dir) / "envs.toml")
    assert envs_file.exists()
    envs = envs_file.read()
    assert envs[venv_name]["minor"] == "3.7"
    assert envs[venv_name]["patch"] == "3.7.1"

<<<<<<< HEAD
    assert env.path == Path(tmp_dir) / f"{venv_name}-py3.7"
=======
    assert env.path == Path(tmp_dir) / "{}-py3.7".format(venv_name)
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    assert env.base == Path("/prefix")


def test_activate_activates_existing_virtualenv_no_envs_file(
<<<<<<< HEAD
    tmp_dir: str,
    manager: EnvManager,
    poetry: "Poetry",
    config: "Config",
    mocker: "MockerFixture",
=======
    tmp_dir, manager, poetry, config, mocker
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))

<<<<<<< HEAD
    os.mkdir(os.path.join(tmp_dir, f"{venv_name}-py3.7"))
=======
    os.mkdir(os.path.join(tmp_dir, "{}-py3.7".format(venv_name)))
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

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

    env = manager.activate("python3.7", NullIO())

    m.assert_not_called()

    envs_file = TOMLFile(Path(tmp_dir) / "envs.toml")
    assert envs_file.exists()
    envs = envs_file.read()
    assert envs[venv_name]["minor"] == "3.7"
    assert envs[venv_name]["patch"] == "3.7.1"

<<<<<<< HEAD
    assert env.path == Path(tmp_dir) / f"{venv_name}-py3.7"
=======
    assert env.path == Path(tmp_dir) / "{}-py3.7".format(venv_name)
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    assert env.base == Path("/prefix")


def test_activate_activates_same_virtualenv_with_envs_file(
<<<<<<< HEAD
    tmp_dir: str,
    manager: EnvManager,
    poetry: "Poetry",
    config: "Config",
    mocker: "MockerFixture",
=======
    tmp_dir, manager, poetry, config, mocker
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))

    envs_file = TOMLFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.1"}
    envs_file.write(doc)

<<<<<<< HEAD
    os.mkdir(os.path.join(tmp_dir, f"{venv_name}-py3.7"))
=======
    os.mkdir(os.path.join(tmp_dir, "{}-py3.7".format(venv_name)))
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

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

    env = manager.activate("python3.7", NullIO())

    m.assert_not_called()

    assert envs_file.exists()
    envs = envs_file.read()
    assert envs[venv_name]["minor"] == "3.7"
    assert envs[venv_name]["patch"] == "3.7.1"

<<<<<<< HEAD
    assert env.path == Path(tmp_dir) / f"{venv_name}-py3.7"
=======
    assert env.path == Path(tmp_dir) / "{}-py3.7".format(venv_name)
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    assert env.base == Path("/prefix")


def test_activate_activates_different_virtualenv_with_envs_file(
<<<<<<< HEAD
    tmp_dir: str,
    manager: EnvManager,
    poetry: "Poetry",
    config: "Config",
    mocker: "MockerFixture",
=======
    tmp_dir, manager, poetry, config, mocker
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))
    envs_file = TOMLFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.1"}
    envs_file.write(doc)

<<<<<<< HEAD
    os.mkdir(os.path.join(tmp_dir, f"{venv_name}-py3.7"))
=======
    os.mkdir(os.path.join(tmp_dir, "{}-py3.7".format(venv_name)))
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

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

    env = manager.activate("python3.6", NullIO())

    m.assert_called_with(
<<<<<<< HEAD
        Path(tmp_dir) / f"{venv_name}-py3.6",
=======
        Path(tmp_dir) / "{}-py3.6".format(venv_name),
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        executable="python3.6",
        flags={"always-copy": False, "system-site-packages": False},
        with_pip=True,
        with_setuptools=True,
        with_wheel=True,
    )

    assert envs_file.exists()
    envs = envs_file.read()
    assert envs[venv_name]["minor"] == "3.6"
    assert envs[venv_name]["patch"] == "3.6.6"

<<<<<<< HEAD
    assert env.path == Path(tmp_dir) / f"{venv_name}-py3.6"
=======
    assert env.path == Path(tmp_dir) / "{}-py3.6".format(venv_name)
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    assert env.base == Path("/prefix")


def test_activate_activates_recreates_for_different_patch(
<<<<<<< HEAD
    tmp_dir: str,
    manager: EnvManager,
    poetry: "Poetry",
    config: "Config",
    mocker: "MockerFixture",
=======
    tmp_dir, manager, poetry, config, mocker
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))
    envs_file = TOMLFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.0"}
    envs_file.write(doc)

<<<<<<< HEAD
    os.mkdir(os.path.join(tmp_dir, f"{venv_name}-py3.7"))
=======
    os.mkdir(os.path.join(tmp_dir, "{}-py3.7".format(venv_name)))
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

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

    env = manager.activate("python3.7", NullIO())

    build_venv_m.assert_called_with(
<<<<<<< HEAD
        Path(tmp_dir) / f"{venv_name}-py3.7",
=======
        Path(tmp_dir) / "{}-py3.7".format(venv_name),
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        executable="python3.7",
        flags={"always-copy": False, "system-site-packages": False},
        with_pip=True,
        with_setuptools=True,
        with_wheel=True,
    )
<<<<<<< HEAD
    remove_venv_m.assert_called_with(Path(tmp_dir) / f"{venv_name}-py3.7")
=======
    remove_venv_m.assert_called_with(Path(tmp_dir) / "{}-py3.7".format(venv_name))
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

    assert envs_file.exists()
    envs = envs_file.read()
    assert envs[venv_name]["minor"] == "3.7"
    assert envs[venv_name]["patch"] == "3.7.1"

<<<<<<< HEAD
    assert env.path == Path(tmp_dir) / f"{venv_name}-py3.7"
    assert env.base == Path("/prefix")
    assert (Path(tmp_dir) / f"{venv_name}-py3.7").exists()


def test_activate_does_not_recreate_when_switching_minor(
    tmp_dir: str,
    manager: EnvManager,
    poetry: "Poetry",
    config: "Config",
    mocker: "MockerFixture",
=======
    assert env.path == Path(tmp_dir) / "{}-py3.7".format(venv_name)
    assert env.base == Path("/prefix")
    assert (Path(tmp_dir) / "{}-py3.7".format(venv_name)).exists()


def test_activate_does_not_recreate_when_switching_minor(
    tmp_dir, manager, poetry, config, mocker
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))
    envs_file = TOMLFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.0"}
    envs_file.write(doc)

<<<<<<< HEAD
    os.mkdir(os.path.join(tmp_dir, f"{venv_name}-py3.7"))
    os.mkdir(os.path.join(tmp_dir, f"{venv_name}-py3.6"))
=======
    os.mkdir(os.path.join(tmp_dir, "{}-py3.7".format(venv_name)))
    os.mkdir(os.path.join(tmp_dir, "{}-py3.6".format(venv_name)))
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

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

    env = manager.activate("python3.6", NullIO())

    build_venv_m.assert_not_called()
    remove_venv_m.assert_not_called()

    assert envs_file.exists()
    envs = envs_file.read()
    assert envs[venv_name]["minor"] == "3.6"
    assert envs[venv_name]["patch"] == "3.6.6"

<<<<<<< HEAD
    assert env.path == Path(tmp_dir) / f"{venv_name}-py3.6"
    assert env.base == Path("/prefix")
    assert (Path(tmp_dir) / f"{venv_name}-py3.6").exists()


def test_deactivate_non_activated_but_existing(
    tmp_dir: str,
    manager: EnvManager,
    poetry: "Poetry",
    config: "Config",
    mocker: "MockerFixture",
=======
    assert env.path == Path(tmp_dir) / "{}-py3.6".format(venv_name)
    assert env.base == Path("/prefix")
    assert (Path(tmp_dir) / "{}-py3.6".format(venv_name)).exists()


def test_deactivate_non_activated_but_existing(
    tmp_dir, manager, poetry, config, mocker
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))

<<<<<<< HEAD
    python = ".".join(str(c) for c in sys.version_info[:2])
    (Path(tmp_dir) / f"{venv_name}-py{python}").mkdir()
=======
    (
        Path(tmp_dir)
        / "{}-py{}".format(venv_name, ".".join(str(c) for c in sys.version_info[:2]))
    ).mkdir()
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(),
    )

    manager.deactivate(NullIO())
    env = manager.get()

<<<<<<< HEAD
    assert env.path == Path(tmp_dir) / f"{venv_name}-py{python}"
    assert Path("/prefix")


def test_deactivate_activated(
    tmp_dir: str,
    manager: EnvManager,
    poetry: "Poetry",
    config: "Config",
    mocker: "MockerFixture",
):
=======
    assert env.path == Path(tmp_dir) / "{}-py{}".format(
        venv_name, ".".join(str(c) for c in sys.version_info[:2])
    )
    assert Path("/prefix")


def test_deactivate_activated(tmp_dir, manager, poetry, config, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))
<<<<<<< HEAD
    version = Version.from_parts(*sys.version_info[:3])
    other_version = Version.parse("3.4") if version.major == 2 else version.next_minor()
    (Path(tmp_dir) / f"{venv_name}-py{version.major}.{version.minor}").mkdir()
    (
        Path(tmp_dir) / f"{venv_name}-py{other_version.major}.{other_version.minor}"
=======
    version = Version.parse(".".join(str(c) for c in sys.version_info[:3]))
    other_version = Version.parse("3.4") if version.major == 2 else version.next_minor()
    (
        Path(tmp_dir) / "{}-py{}.{}".format(venv_name, version.major, version.minor)
    ).mkdir()
    (
        Path(tmp_dir)
        / "{}-py{}.{}".format(venv_name, other_version.major, other_version.minor)
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    ).mkdir()

    envs_file = TOMLFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {
<<<<<<< HEAD
        "minor": f"{other_version.major}.{other_version.minor}",
=======
        "minor": "{}.{}".format(other_version.major, other_version.minor),
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        "patch": other_version.text,
    }
    envs_file.write(doc)

    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(),
    )

    manager.deactivate(NullIO())
    env = manager.get()

<<<<<<< HEAD
    assert env.path == Path(tmp_dir) / f"{venv_name}-py{version.major}.{version.minor}"
=======
    assert env.path == Path(tmp_dir) / "{}-py{}.{}".format(
        venv_name, version.major, version.minor
    )
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    assert Path("/prefix")

    envs = envs_file.read()
    assert len(envs) == 0


def test_get_prefers_explicitly_activated_virtualenvs_over_env_var(
<<<<<<< HEAD
    tmp_dir: str,
    manager: EnvManager,
    poetry: "Poetry",
    config: "Config",
    mocker: "MockerFixture",
=======
    tmp_dir, manager, poetry, config, mocker
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    os.environ["VIRTUAL_ENV"] = "/environment/prefix"

    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))

    config.merge({"virtualenvs": {"path": str(tmp_dir)}})
<<<<<<< HEAD
    (Path(tmp_dir) / f"{venv_name}-py3.7").mkdir()
=======
    (Path(tmp_dir) / "{}-py3.7".format(venv_name)).mkdir()
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

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

<<<<<<< HEAD
    assert env.path == Path(tmp_dir) / f"{venv_name}-py3.7"
    assert env.base == Path("/prefix")


def test_list(tmp_dir: str, manager: EnvManager, poetry: "Poetry", config: "Config"):
    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))
    (Path(tmp_dir) / f"{venv_name}-py3.7").mkdir()
    (Path(tmp_dir) / f"{venv_name}-py3.6").mkdir()

    venvs = manager.list()

    assert len(venvs) == 2
    assert (Path(tmp_dir) / f"{venv_name}-py3.6") == venvs[0].path
    assert (Path(tmp_dir) / f"{venv_name}-py3.7") == venvs[1].path


def test_remove_by_python_version(
    tmp_dir: str,
    manager: EnvManager,
    poetry: "Poetry",
    config: "Config",
    mocker: "MockerFixture",
):
    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))
    (Path(tmp_dir) / f"{venv_name}-py3.7").mkdir()
    (Path(tmp_dir) / f"{venv_name}-py3.6").mkdir()
=======
    assert env.path == Path(tmp_dir) / "{}-py3.7".format(venv_name)
    assert env.base == Path("/prefix")


def test_list(tmp_dir, manager, poetry, config):
    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))
    (Path(tmp_dir) / "{}-py3.7".format(venv_name)).mkdir()
    (Path(tmp_dir) / "{}-py3.6".format(venv_name)).mkdir()

    venvs = manager.list()

    assert 2 == len(venvs)
    assert (Path(tmp_dir) / "{}-py3.6".format(venv_name)) == venvs[0].path
    assert (Path(tmp_dir) / "{}-py3.7".format(venv_name)) == venvs[1].path


def test_remove_by_python_version(tmp_dir, manager, poetry, config, mocker):
    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))
    (Path(tmp_dir) / "{}-py3.7".format(venv_name)).mkdir()
    (Path(tmp_dir) / "{}-py3.6".format(venv_name)).mkdir()
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )

    venv = manager.remove("3.6")

<<<<<<< HEAD
    assert (Path(tmp_dir) / f"{venv_name}-py3.6") == venv.path
    assert not (Path(tmp_dir) / f"{venv_name}-py3.6").exists()


def test_remove_by_name(
    tmp_dir: str,
    manager: EnvManager,
    poetry: "Poetry",
    config: "Config",
    mocker: "MockerFixture",
):
    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))
    (Path(tmp_dir) / f"{venv_name}-py3.7").mkdir()
    (Path(tmp_dir) / f"{venv_name}-py3.6").mkdir()
=======
    assert (Path(tmp_dir) / "{}-py3.6".format(venv_name)) == venv.path
    assert not (Path(tmp_dir) / "{}-py3.6".format(venv_name)).exists()


def test_remove_by_name(tmp_dir, manager, poetry, config, mocker):
    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))
    (Path(tmp_dir) / "{}-py3.7".format(venv_name)).mkdir()
    (Path(tmp_dir) / "{}-py3.6".format(venv_name)).mkdir()
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )

<<<<<<< HEAD
    venv = manager.remove(f"{venv_name}-py3.6")

    assert (Path(tmp_dir) / f"{venv_name}-py3.6") == venv.path
    assert not (Path(tmp_dir) / f"{venv_name}-py3.6").exists()


def test_remove_also_deactivates(
    tmp_dir: str,
    manager: EnvManager,
    poetry: "Poetry",
    config: "Config",
    mocker: "MockerFixture",
):
    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))
    (Path(tmp_dir) / f"{venv_name}-py3.7").mkdir()
    (Path(tmp_dir) / f"{venv_name}-py3.6").mkdir()
=======
    venv = manager.remove("{}-py3.6".format(venv_name))

    assert (Path(tmp_dir) / "{}-py3.6".format(venv_name)) == venv.path
    assert not (Path(tmp_dir) / "{}-py3.6".format(venv_name)).exists()


def test_remove_also_deactivates(tmp_dir, manager, poetry, config, mocker):
    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))
    (Path(tmp_dir) / "{}-py3.7".format(venv_name)).mkdir()
    (Path(tmp_dir) / "{}-py3.6".format(venv_name)).mkdir()
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )

    envs_file = TOMLFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.6", "patch": "3.6.6"}
    envs_file.write(doc)

    venv = manager.remove("python3.6")

<<<<<<< HEAD
    assert (Path(tmp_dir) / f"{venv_name}-py3.6") == venv.path
    assert not (Path(tmp_dir) / f"{venv_name}-py3.6").exists()
=======
    assert (Path(tmp_dir) / "{}-py3.6".format(venv_name)) == venv.path
    assert not (Path(tmp_dir) / "{}-py3.6".format(venv_name)).exists()
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

    envs = envs_file.read()
    assert venv_name not in envs


<<<<<<< HEAD
def test_remove_keeps_dir_if_not_deleteable(
    tmp_dir: str,
    manager: EnvManager,
    poetry: "Poetry",
    config: "Config",
    mocker: "MockerFixture",
):
=======
def test_remove_keeps_dir_if_not_deleteable(tmp_dir, manager, poetry, config, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    # Ensure we empty rather than delete folder if its is an active mount point.
    # See https://github.com/python-poetry/poetry/pull/2064
    config.merge({"virtualenvs": {"path": str(tmp_dir)}})

    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))
<<<<<<< HEAD
    venv_path = Path(tmp_dir) / f"{venv_name}-py3.6"
=======
    venv_path = Path(tmp_dir) / "{}-py3.6".format(venv_name)
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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

    original_rmtree = shutil.rmtree

<<<<<<< HEAD
    def err_on_rm_venv_only(path: str, *args: Any, **kwargs: Any) -> None:
=======
    def err_on_rm_venv_only(path, *args, **kwargs):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        if path == str(venv_path):
            raise OSError(16, "Test error")  # ERRNO 16: Device or resource busy
        else:
            original_rmtree(path)

    m = mocker.patch("shutil.rmtree", side_effect=err_on_rm_venv_only)

<<<<<<< HEAD
    venv = manager.remove(f"{venv_name}-py3.6")
=======
    venv = manager.remove("{}-py3.6".format(venv_name))
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

    m.assert_any_call(str(venv_path))

    assert venv_path == venv.path
    assert venv_path.exists()

    assert not folder1_path.exists()
    assert not file1_path.exists()
    assert not file2_path.exists()

    m.side_effect = original_rmtree  # Avoid teardown using `err_on_rm_venv_only`


@pytest.mark.skipif(os.name == "nt", reason="Symlinks are not support for Windows")
<<<<<<< HEAD
def test_env_has_symlinks_on_nix(tmp_dir: str, tmp_venv: VirtualEnv):
    assert os.path.islink(tmp_venv.python)


def test_run_with_input(tmp_dir: str, tmp_venv: VirtualEnv):
=======
def test_env_has_symlinks_on_nix(tmp_dir, tmp_venv):
    assert os.path.islink(tmp_venv.python)


def test_run_with_input(tmp_dir, tmp_venv):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    result = tmp_venv.run("python", "-", input_=MINIMAL_SCRIPT)

    assert result == "Minimal Output" + os.linesep


<<<<<<< HEAD
def test_run_with_input_non_zero_return(tmp_dir: str, tmp_venv: VirtualEnv):

    with pytest.raises(EnvCommandError) as process_error:
        # Test command that will return non-zero returncode.
        tmp_venv.run("python", "-", input_=ERRORING_SCRIPT)

    assert process_error.value.e.returncode == 1


def test_run_with_keyboard_interrupt(
    tmp_dir: str, tmp_venv: VirtualEnv, mocker: "MockerFixture"
):
=======
def test_run_with_input_non_zero_return(tmp_dir, tmp_venv):

    with pytest.raises(EnvCommandError) as processError:
        # Test command that will return non-zero returncode.
        tmp_venv.run("python", "-", input_=ERRORING_SCRIPT)

    assert processError.value.e.returncode == 1


def test_run_with_keyboard_interrupt(tmp_dir, tmp_venv, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    mocker.patch("subprocess.run", side_effect=KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        tmp_venv.run("python", "-", input_=MINIMAL_SCRIPT)
    subprocess.run.assert_called_once()


<<<<<<< HEAD
def test_call_with_input_and_keyboard_interrupt(
    tmp_dir: str, tmp_venv: VirtualEnv, mocker: "MockerFixture"
):
=======
def test_call_with_input_and_keyboard_interrupt(tmp_dir, tmp_venv, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    mocker.patch("subprocess.run", side_effect=KeyboardInterrupt())
    kwargs = {"call": True}
    with pytest.raises(KeyboardInterrupt):
        tmp_venv.run("python", "-", input_=MINIMAL_SCRIPT, **kwargs)
    subprocess.run.assert_called_once()


<<<<<<< HEAD
def test_call_no_input_with_keyboard_interrupt(
    tmp_dir: str, tmp_venv: VirtualEnv, mocker: "MockerFixture"
):
=======
def test_call_no_input_with_keyboard_interrupt(tmp_dir, tmp_venv, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    mocker.patch("subprocess.call", side_effect=KeyboardInterrupt())
    kwargs = {"call": True}
    with pytest.raises(KeyboardInterrupt):
        tmp_venv.run("python", "-", **kwargs)
    subprocess.call.assert_called_once()


<<<<<<< HEAD
def test_run_with_called_process_error(
    tmp_dir: str, tmp_venv: VirtualEnv, mocker: "MockerFixture"
):
=======
def test_run_with_called_process_error(tmp_dir, tmp_venv, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    mocker.patch(
        "subprocess.run", side_effect=subprocess.CalledProcessError(42, "some_command")
    )
    with pytest.raises(EnvCommandError):
        tmp_venv.run("python", "-", input_=MINIMAL_SCRIPT)
    subprocess.run.assert_called_once()


<<<<<<< HEAD
def test_call_with_input_and_called_process_error(
    tmp_dir: str, tmp_venv: VirtualEnv, mocker: "MockerFixture"
):
=======
def test_call_with_input_and_called_process_error(tmp_dir, tmp_venv, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    mocker.patch(
        "subprocess.run", side_effect=subprocess.CalledProcessError(42, "some_command")
    )
    kwargs = {"call": True}
    with pytest.raises(EnvCommandError):
        tmp_venv.run("python", "-", input_=MINIMAL_SCRIPT, **kwargs)
    subprocess.run.assert_called_once()


<<<<<<< HEAD
def test_call_no_input_with_called_process_error(
    tmp_dir: str, tmp_venv: VirtualEnv, mocker: "MockerFixture"
):
=======
def test_call_no_input_with_called_process_error(tmp_dir, tmp_venv, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    mocker.patch(
        "subprocess.call", side_effect=subprocess.CalledProcessError(42, "some_command")
    )
    kwargs = {"call": True}
    with pytest.raises(EnvCommandError):
        tmp_venv.run("python", "-", **kwargs)
    subprocess.call.assert_called_once()


def test_create_venv_tries_to_find_a_compatible_python_executable_using_generic_ones_first(
<<<<<<< HEAD
    manager: EnvManager,
    poetry: "Poetry",
    config: "Config",
    mocker: "MockerFixture",
    config_virtualenvs_path: Path,
=======
    manager, poetry, config, mocker, config_virtualenvs_path
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    poetry.package.python_versions = "^3.6"
    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))

    mocker.patch("sys.version_info", (2, 7, 16))
    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.7.5")),
    )
    m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=lambda *args, **kwargs: ""
    )

    manager.create_venv(NullIO())

    m.assert_called_with(
<<<<<<< HEAD
        config_virtualenvs_path / f"{venv_name}-py3.7",
=======
        config_virtualenvs_path / "{}-py3.7".format(venv_name),
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        executable="python3",
        flags={"always-copy": False, "system-site-packages": False},
        with_pip=True,
        with_setuptools=True,
        with_wheel=True,
    )


def test_create_venv_tries_to_find_a_compatible_python_executable_using_specific_ones(
<<<<<<< HEAD
    manager: EnvManager,
    poetry: "Poetry",
    config: "Config",
    mocker: "MockerFixture",
    config_virtualenvs_path: Path,
=======
    manager, poetry, config, mocker, config_virtualenvs_path
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    poetry.package.python_versions = "^3.6"
    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))

    mocker.patch("sys.version_info", (2, 7, 16))
    mocker.patch("subprocess.check_output", side_effect=["3.5.3", "3.9.0"])
    m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=lambda *args, **kwargs: ""
    )

    manager.create_venv(NullIO())

    m.assert_called_with(
<<<<<<< HEAD
        config_virtualenvs_path / f"{venv_name}-py3.9",
=======
        config_virtualenvs_path / "{}-py3.9".format(venv_name),
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        executable="python3.9",
        flags={"always-copy": False, "system-site-packages": False},
        with_pip=True,
        with_setuptools=True,
        with_wheel=True,
    )


def test_create_venv_fails_if_no_compatible_python_version_could_be_found(
<<<<<<< HEAD
    manager: EnvManager, poetry: "Poetry", config: "Config", mocker: "MockerFixture"
=======
    manager, poetry, config, mocker
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    poetry.package.python_versions = "^4.8"

    mocker.patch("subprocess.check_output", side_effect=["", "", "", ""])
    m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=lambda *args, **kwargs: ""
    )

    with pytest.raises(NoCompatiblePythonVersionFound) as e:
        manager.create_venv(NullIO())

    expected_message = (
        "Poetry was unable to find a compatible version. "
        "If you have one, you can explicitly use it "
        'via the "env use" command.'
    )

    assert expected_message == str(e.value)
<<<<<<< HEAD
    assert m.call_count == 0


def test_create_venv_does_not_try_to_find_compatible_versions_with_executable(
    manager: EnvManager, poetry: "Poetry", config: "Config", mocker: "MockerFixture"
=======
    assert 0 == m.call_count


def test_create_venv_does_not_try_to_find_compatible_versions_with_executable(
    manager, poetry, config, mocker
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    poetry.package.python_versions = "^4.8"

    mocker.patch("subprocess.check_output", side_effect=["3.8.0"])
    m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=lambda *args, **kwargs: ""
    )

    with pytest.raises(NoCompatiblePythonVersionFound) as e:
        manager.create_venv(NullIO(), executable="3.8")

    expected_message = (
        "The specified Python version (3.8.0) is not supported by the project (^4.8).\n"
        "Please choose a compatible version or loosen the python constraint "
        "specified in the pyproject.toml file."
    )

    assert expected_message == str(e.value)
<<<<<<< HEAD
    assert m.call_count == 0


def test_create_venv_uses_patch_version_to_detect_compatibility(
    manager: EnvManager,
    poetry: "Poetry",
    config: "Config",
    mocker: "MockerFixture",
    config_virtualenvs_path: Path,
=======
    assert 0 == m.call_count


def test_create_venv_uses_patch_version_to_detect_compatibility(
    manager, poetry, config, mocker, config_virtualenvs_path
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

<<<<<<< HEAD
    version = Version.from_parts(*sys.version_info[:3])
    poetry.package.python_versions = "^" + ".".join(
        str(c) for c in sys.version_info[:3]
=======
    version = Version.parse(".".join(str(c) for c in sys.version_info[:3]))
    poetry.package.python_versions = "^{}".format(
        ".".join(str(c) for c in sys.version_info[:3])
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    )
    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))

    mocker.patch("sys.version_info", (version.major, version.minor, version.patch + 1))
    check_output = mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.9")),
    )
    m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=lambda *args, **kwargs: ""
    )

    manager.create_venv(NullIO())

    assert not check_output.called
    m.assert_called_with(
<<<<<<< HEAD
        config_virtualenvs_path / f"{venv_name}-py{version.major}.{version.minor}",
=======
        config_virtualenvs_path
        / "{}-py{}.{}".format(venv_name, version.major, version.minor),
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        executable=None,
        flags={"always-copy": False, "system-site-packages": False},
        with_pip=True,
        with_setuptools=True,
        with_wheel=True,
    )


def test_create_venv_uses_patch_version_to_detect_compatibility_with_executable(
<<<<<<< HEAD
    manager: EnvManager,
    poetry: "Poetry",
    config: "Config",
    mocker: "MockerFixture",
    config_virtualenvs_path: Path,
=======
    manager, poetry, config, mocker, config_virtualenvs_path
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

<<<<<<< HEAD
    version = Version.from_parts(*sys.version_info[:3])
    poetry.package.python_versions = f"~{version.major}.{version.minor-1}.0"
=======
    version = Version.parse(".".join(str(c) for c in sys.version_info[:3]))
    poetry.package.python_versions = "~{}".format(
        ".".join(str(c) for c in (version.major, version.minor - 1, 0))
    )
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))

    check_output = mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(
<<<<<<< HEAD
            Version.parse(f"{version.major}.{version.minor - 1}.0")
=======
            Version.parse("{}.{}.0".format(version.major, version.minor - 1))
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        ),
    )
    m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=lambda *args, **kwargs: ""
    )

    manager.create_venv(
<<<<<<< HEAD
        NullIO(), executable=f"python{version.major}.{version.minor - 1}"
=======
        NullIO(), executable="python{}.{}".format(version.major, version.minor - 1)
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    )

    assert check_output.called
    m.assert_called_with(
<<<<<<< HEAD
        config_virtualenvs_path / f"{venv_name}-py{version.major}.{version.minor - 1}",
        executable=f"python{version.major}.{version.minor - 1}",
=======
        config_virtualenvs_path
        / "{}-py{}.{}".format(venv_name, version.major, version.minor - 1),
        executable="python{}.{}".format(version.major, version.minor - 1),
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        flags={"always-copy": False, "system-site-packages": False},
        with_pip=True,
        with_setuptools=True,
        with_wheel=True,
    )


def test_activate_with_in_project_setting_does_not_fail_if_no_venvs_dir(
<<<<<<< HEAD
    manager: EnvManager,
    poetry: "Poetry",
    config: "Config",
    tmp_dir: str,
    mocker: "MockerFixture",
=======
    manager, poetry, config, tmp_dir, mocker
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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

    manager.activate("python3.7", NullIO())

    m.assert_called_with(
        poetry.file.parent / ".venv",
        executable="python3.7",
        flags={"always-copy": False, "system-site-packages": False},
        with_pip=True,
        with_setuptools=True,
        with_wheel=True,
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
<<<<<<< HEAD
    "enabled",
    [True, False],
)
def test_system_env_usersite(mocker: "MockerFixture", enabled: bool):
=======
    ("enabled",),
    [(True,), (False,)],
)
def test_system_env_usersite(mocker, enabled):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    mocker.patch("site.check_enableusersite", return_value=enabled)
    env = SystemEnv(Path(sys.prefix))
    assert (enabled and env.usersite is not None) or (
        not enabled and env.usersite is None
    )


<<<<<<< HEAD
def test_venv_has_correct_paths(tmp_venv: VirtualEnv):
=======
def test_venv_has_correct_paths(tmp_venv):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    paths = tmp_venv.paths

    assert paths.get("purelib") is not None
    assert paths.get("platlib") is not None
    assert paths.get("scripts") is not None
    assert tmp_venv.site_packages.path == Path(paths["purelib"])


<<<<<<< HEAD
def test_env_system_packages(tmp_path: Path, poetry: "Poetry"):
    venv_path = tmp_path / "venv"
    pyvenv_cfg = venv_path / "pyvenv.cfg"

    EnvManager(poetry).build_venv(path=venv_path, flags={"system-site-packages": True})

    assert "include-system-site-packages = true" in pyvenv_cfg.read_text()


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
    poetry: "Poetry",
    config: "Config",
    mocker: "MockerFixture",
    config_virtualenvs_path: Path,
):
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    poetry.package.python_versions = "~3.5.1"
    venv_name = manager.generate_env_name("simple-project", str(poetry.file.parent))

    check_output = mocker.patch(
        "subprocess.check_output",
        side_effect=lambda cmd, *args, **kwargs: str(
            "3.5.12" if "python3.5" in cmd else "3.7.1"
        ),
    )
    m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=lambda *args, **kwargs: ""
    )

    manager.create_venv(NullIO())

    assert check_output.called
    m.assert_called_with(
        config_virtualenvs_path / f"{venv_name}-py3.5",
        executable="python3.5",
        flags={"always-copy": False, "system-site-packages": False},
        with_pip=True,
        with_setuptools=True,
        with_wheel=True,
    )


def test_generate_env_name_ignores_case_for_case_insensitive_fs(tmp_dir: str):
    venv_name1 = EnvManager.generate_env_name("simple-project", "MyDiR")
    venv_name2 = EnvManager.generate_env_name("simple-project", "mYdIr")
    if sys.platform == "win32":
        assert venv_name1 == venv_name2
    else:
        assert venv_name1 != venv_name2
=======
def test_env_system_packages(tmp_path, config):
    venv_path = tmp_path / "venv"
    pyvenv_cfg = venv_path / "pyvenv.cfg"

    EnvManager(config).build_venv(path=venv_path, flags={"system-site-packages": True})

    if sys.version_info >= (3, 3):
        assert "include-system-site-packages = true" in pyvenv_cfg.read_text()
    elif (2, 6) < sys.version_info < (3, 0):
        assert not venv_path.joinpath(
            "lib", "python2.7", "no-global-site-packages.txt"
        ).exists()
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
