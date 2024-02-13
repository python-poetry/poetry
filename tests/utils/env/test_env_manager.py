from __future__ import annotations

import logging
import os
import sys

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest
import tomlkit

from poetry.core.constraints.version import Version

from poetry.toml.file import TOMLFile
from poetry.utils.env import GET_BASE_PREFIX
from poetry.utils.env import GET_PYTHON_VERSION_ONELINER
from poetry.utils.env import EnvManager
from poetry.utils.env import IncorrectEnvError
from poetry.utils.env import InvalidCurrentPythonVersionError
from poetry.utils.env import NoCompatiblePythonVersionFound
from poetry.utils.env import PythonVersionNotFound
from poetry.utils.env.env_manager import EnvsFile
from poetry.utils.helpers import remove_directory


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterator

    from _pytest.logging import LogCaptureFixture
    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry
    from tests.conftest import Config
    from tests.types import FixtureDirGetter
    from tests.types import ProjectFactory


VERSION_3_7_1 = Version.parse("3.7.1")


def build_venv(path: Path | str, **__: Any) -> None:
    os.mkdir(str(path))


def check_output_wrapper(
    version: Version = VERSION_3_7_1,
) -> Callable[[list[str], Any, Any], str]:
    def check_output(cmd: list[str], *args: Any, **kwargs: Any) -> str:
        # cmd is a list, like ["python", "-c", "do stuff"]
        python_cmd = cmd[-1]
        if "print(json.dumps(env))" in python_cmd:
            return (
                f'{{"version_info": [{version.major}, {version.minor},'
                f" {version.patch}]}}"
            )

        if "sys.version_info[:3]" in python_cmd:
            return version.text

        if "sys.version_info[:2]" in python_cmd:
            return f"{version.major}.{version.minor}"

        if "import sys; print(sys.executable)" in python_cmd:
            executable = cmd[0]
            basename = os.path.basename(executable)
            return f"/usr/bin/{basename}"

        if "print(sys.base_prefix)" in python_cmd:
            return sys.base_prefix

        assert "import sys; print(sys.prefix)" in python_cmd
        return "/prefix"

    return check_output


@pytest.fixture
def in_project_venv_dir(poetry: Poetry) -> Iterator[Path]:
    os.environ.pop("VIRTUAL_ENV", None)
    venv_dir = poetry.file.path.parent.joinpath(".venv")
    venv_dir.mkdir()
    try:
        yield venv_dir
    finally:
        venv_dir.rmdir()


@pytest.mark.parametrize(
    ("section", "version", "expected"),
    [
        ("foo", None, "3.10"),
        ("bar", None, "3.11"),
        ("baz", None, "3.12"),
        ("bar", "3.11", "3.11"),
        ("bar", "3.10", None),
    ],
)
def test_envs_file_remove_section(
    tmp_path: Path, section: str, version: str | None, expected: str | None
) -> None:
    envs_file_path = tmp_path / "envs.toml"

    envs_file = TOMLFile(envs_file_path)
    doc = tomlkit.document()
    doc["foo"] = {"minor": "3.10", "patch": "3.10.13"}
    doc["bar"] = {"minor": "3.11", "patch": "3.11.7"}
    doc["baz"] = {"minor": "3.12", "patch": "3.12.1"}
    envs_file.write(doc)

    minor = EnvsFile(envs_file_path).remove_section(section, version)

    assert minor == expected

    envs = TOMLFile(envs_file_path).read()
    if expected is None:
        assert section in envs
    else:
        assert section not in envs
    for other_section in {"foo", "bar", "baz"} - {section}:
        assert other_section in envs


def test_activate_in_project_venv_no_explicit_config(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    mocker: MockerFixture,
    venv_name: str,
    in_project_venv_dir: Path,
) -> None:
    mocker.patch("shutil.which", side_effect=lambda py: f"/usr/bin/{py}")
    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(),
    )
    m = mocker.patch("poetry.utils.env.EnvManager.build_venv", side_effect=build_venv)

    env = manager.activate("python3.7")

    assert env.path == tmp_path / "poetry-fixture-simple" / ".venv"
    assert env.base == Path(sys.base_prefix)

    m.assert_called_with(
        tmp_path / "poetry-fixture-simple" / ".venv",
        executable=Path("/usr/bin/python3.7"),
        flags={
            "always-copy": False,
            "system-site-packages": False,
            "no-pip": False,
            "no-setuptools": False,
        },
        prompt="simple-project-py3.7",
    )

    envs_file = TOMLFile(tmp_path / "envs.toml")
    assert not envs_file.exists()


def test_activate_activates_non_existing_virtualenv_no_envs_file(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
    venv_flags_default: dict[str, bool],
) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    config.merge({"virtualenvs": {"path": str(tmp_path)}})

    mocker.patch("shutil.which", side_effect=lambda py: f"/usr/bin/{py}")
    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(),
    )
    m = mocker.patch("poetry.utils.env.EnvManager.build_venv", side_effect=build_venv)

    env = manager.activate("python3.7")

    m.assert_called_with(
        tmp_path / f"{venv_name}-py3.7",
        executable=Path("/usr/bin/python3.7"),
        flags=venv_flags_default,
        prompt="simple-project-py3.7",
    )

    envs_file = TOMLFile(tmp_path / "envs.toml")

    assert envs_file.exists()
    envs: dict[str, Any] = envs_file.read()
    assert envs[venv_name]["minor"] == "3.7"
    assert envs[venv_name]["patch"] == "3.7.1"

    assert env.path == tmp_path / f"{venv_name}-py3.7"
    assert env.base == Path(sys.base_prefix)


def test_activate_fails_when_python_cannot_be_found(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    os.mkdir(tmp_path / f"{venv_name}-py3.7")

    config.merge({"virtualenvs": {"path": str(tmp_path)}})

    mocker.patch("shutil.which", return_value=None)

    with pytest.raises(PythonVersionNotFound) as e:
        manager.activate("python3.7")

    expected_message = "Could not find the python executable python3.7"
    assert str(e.value) == expected_message


def test_activate_activates_existing_virtualenv_no_envs_file(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    os.mkdir(tmp_path / f"{venv_name}-py3.7")

    config.merge({"virtualenvs": {"path": str(tmp_path)}})

    mocker.patch("shutil.which", side_effect=lambda py: f"/usr/bin/{py}")
    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(),
    )
    m = mocker.patch("poetry.utils.env.EnvManager.build_venv", side_effect=build_venv)

    env = manager.activate("python3.7")

    m.assert_not_called()

    envs_file = TOMLFile(tmp_path / "envs.toml")
    assert envs_file.exists()
    envs: dict[str, Any] = envs_file.read()
    assert envs[venv_name]["minor"] == "3.7"
    assert envs[venv_name]["patch"] == "3.7.1"

    assert env.path == tmp_path / f"{venv_name}-py3.7"
    assert env.base == Path(sys.base_prefix)


def test_activate_activates_same_virtualenv_with_envs_file(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    envs_file = TOMLFile(tmp_path / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.1"}
    envs_file.write(doc)

    os.mkdir(tmp_path / f"{venv_name}-py3.7")

    config.merge({"virtualenvs": {"path": str(tmp_path)}})

    mocker.patch("shutil.which", side_effect=lambda py: f"/usr/bin/{py}")
    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(),
    )
    m = mocker.patch("poetry.utils.env.EnvManager.create_venv")

    env = manager.activate("python3.7")

    m.assert_not_called()

    assert envs_file.exists()
    envs: dict[str, Any] = envs_file.read()
    assert envs[venv_name]["minor"] == "3.7"
    assert envs[venv_name]["patch"] == "3.7.1"

    assert env.path == tmp_path / f"{venv_name}-py3.7"
    assert env.base == Path(sys.base_prefix)


def test_activate_activates_different_virtualenv_with_envs_file(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
    venv_flags_default: dict[str, bool],
) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    envs_file = TOMLFile(tmp_path / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.1"}
    envs_file.write(doc)

    os.mkdir(tmp_path / f"{venv_name}-py3.7")

    config.merge({"virtualenvs": {"path": str(tmp_path)}})

    mocker.patch("shutil.which", side_effect=lambda py: f"/usr/bin/{py}")
    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )
    m = mocker.patch("poetry.utils.env.EnvManager.build_venv", side_effect=build_venv)

    env = manager.activate("python3.6")

    m.assert_called_with(
        tmp_path / f"{venv_name}-py3.6",
        executable=Path("/usr/bin/python3.6"),
        flags=venv_flags_default,
        prompt="simple-project-py3.6",
    )

    assert envs_file.exists()
    envs: dict[str, Any] = envs_file.read()
    assert envs[venv_name]["minor"] == "3.6"
    assert envs[venv_name]["patch"] == "3.6.6"

    assert env.path == tmp_path / f"{venv_name}-py3.6"
    assert env.base == Path(sys.base_prefix)


def test_activate_activates_recreates_for_different_patch(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
    venv_flags_default: dict[str, bool],
) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    envs_file = TOMLFile(tmp_path / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.0"}
    envs_file.write(doc)

    os.mkdir(tmp_path / f"{venv_name}-py3.7")

    config.merge({"virtualenvs": {"path": str(tmp_path)}})

    mocker.patch("shutil.which", side_effect=lambda py: f"/usr/bin/{py}")
    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(),
    )
    build_venv_m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=build_venv
    )
    remove_venv_m = mocker.patch(
        "poetry.utils.env.EnvManager.remove_venv", side_effect=EnvManager.remove_venv
    )

    env = manager.activate("python3.7")

    build_venv_m.assert_called_with(
        tmp_path / f"{venv_name}-py3.7",
        executable=Path("/usr/bin/python3.7"),
        flags=venv_flags_default,
        prompt="simple-project-py3.7",
    )
    remove_venv_m.assert_called_with(tmp_path / f"{venv_name}-py3.7")

    assert envs_file.exists()
    envs: dict[str, Any] = envs_file.read()
    assert envs[venv_name]["minor"] == "3.7"
    assert envs[venv_name]["patch"] == "3.7.1"

    assert env.path == tmp_path / f"{venv_name}-py3.7"
    assert env.base == Path(sys.base_prefix)
    assert (tmp_path / f"{venv_name}-py3.7").exists()


def test_activate_does_not_recreate_when_switching_minor(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    envs_file = TOMLFile(tmp_path / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.0"}
    envs_file.write(doc)

    os.mkdir(tmp_path / f"{venv_name}-py3.7")
    os.mkdir(tmp_path / f"{venv_name}-py3.6")

    config.merge({"virtualenvs": {"path": str(tmp_path)}})

    mocker.patch("shutil.which", side_effect=lambda py: f"/usr/bin/{py}")
    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
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
    envs: dict[str, Any] = envs_file.read()
    assert envs[venv_name]["minor"] == "3.6"
    assert envs[venv_name]["patch"] == "3.6.6"

    assert env.path == tmp_path / f"{venv_name}-py3.6"
    assert env.base == Path(sys.base_prefix)
    assert (tmp_path / f"{venv_name}-py3.6").exists()


def test_activate_with_in_project_setting_does_not_fail_if_no_venvs_dir(
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    tmp_path: Path,
    mocker: MockerFixture,
    venv_flags_default: dict[str, bool],
) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    config.merge(
        {
            "virtualenvs": {
                "path": str(tmp_path / "virtualenvs"),
                "in-project": True,
            }
        }
    )

    mocker.patch("shutil.which", side_effect=lambda py: f"/usr/bin/{py}")
    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(),
    )
    m = mocker.patch("poetry.utils.env.EnvManager.build_venv")

    manager.activate("python3.7")

    m.assert_called_with(
        poetry.file.path.parent / ".venv",
        executable=Path("/usr/bin/python3.7"),
        flags=venv_flags_default,
        prompt="simple-project-py3.7",
    )

    envs_file = TOMLFile(tmp_path / "virtualenvs" / "envs.toml")
    assert not envs_file.exists()


def test_deactivate_non_activated_but_existing(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    python = ".".join(str(c) for c in sys.version_info[:2])
    (tmp_path / f"{venv_name}-py{python}").mkdir()

    config.merge({"virtualenvs": {"path": str(tmp_path)}})

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(),
    )

    manager.deactivate()
    env = manager.get()

    assert env.path == tmp_path / f"{venv_name}-py{python}"


def test_deactivate_activated(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    version = Version.from_parts(*sys.version_info[:3])
    other_version = Version.parse("3.4") if version.major == 2 else version.next_minor()
    (tmp_path / f"{venv_name}-py{version.major}.{version.minor}").mkdir()
    (tmp_path / f"{venv_name}-py{other_version.major}.{other_version.minor}").mkdir()

    envs_file = TOMLFile(tmp_path / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {
        "minor": f"{other_version.major}.{other_version.minor}",
        "patch": other_version.text,
    }
    envs_file.write(doc)

    config.merge({"virtualenvs": {"path": str(tmp_path)}})

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(),
    )

    manager.deactivate()
    env = manager.get()

    assert env.path == tmp_path / f"{venv_name}-py{version.major}.{version.minor}"

    envs = envs_file.read()
    assert len(envs) == 0


@pytest.mark.parametrize("in_project", [True, False, None])
def test_get_venv_with_venv_folder_present(
    manager: EnvManager,
    poetry: Poetry,
    in_project_venv_dir: Path,
    in_project: bool | None,
) -> None:
    poetry.config.config["virtualenvs"]["in-project"] = in_project
    venv = manager.get()
    if in_project is False:
        assert venv.path != in_project_venv_dir
    else:
        assert venv.path == in_project_venv_dir


def test_get_prefers_explicitly_activated_virtualenvs_over_env_var(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
) -> None:
    os.environ["VIRTUAL_ENV"] = "/environment/prefix"

    config.merge({"virtualenvs": {"path": str(tmp_path)}})
    (tmp_path / f"{venv_name}-py3.7").mkdir()

    envs_file = TOMLFile(tmp_path / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.0"}
    envs_file.write(doc)

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(),
    )

    env = manager.get()

    assert env.path == tmp_path / f"{venv_name}-py3.7"
    assert env.base == Path(sys.base_prefix)


def test_list(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    venv_name: str,
) -> None:
    config.merge({"virtualenvs": {"path": str(tmp_path)}})

    (tmp_path / f"{venv_name}-py3.7").mkdir()
    (tmp_path / f"{venv_name}-py3.6").mkdir()

    venvs = manager.list()

    assert len(venvs) == 2
    assert venvs[0].path == tmp_path / f"{venv_name}-py3.6"
    assert venvs[1].path == tmp_path / f"{venv_name}-py3.7"


def test_remove_by_python_version(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
) -> None:
    config.merge({"virtualenvs": {"path": str(tmp_path)}})

    (tmp_path / f"{venv_name}-py3.7").mkdir()
    (tmp_path / f"{venv_name}-py3.6").mkdir()

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )

    venv = manager.remove("3.6")

    expected_venv_path = tmp_path / f"{venv_name}-py3.6"
    assert venv.path == expected_venv_path
    assert not expected_venv_path.exists()


def test_remove_by_name(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
) -> None:
    config.merge({"virtualenvs": {"path": str(tmp_path)}})

    (tmp_path / f"{venv_name}-py3.7").mkdir()
    (tmp_path / f"{venv_name}-py3.6").mkdir()

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )

    venv = manager.remove(f"{venv_name}-py3.6")

    expected_venv_path = tmp_path / f"{venv_name}-py3.6"
    assert venv.path == expected_venv_path
    assert not expected_venv_path.exists()


def test_remove_by_string_with_python_and_version(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
) -> None:
    config.merge({"virtualenvs": {"path": str(tmp_path)}})

    (tmp_path / f"{venv_name}-py3.7").mkdir()
    (tmp_path / f"{venv_name}-py3.6").mkdir()

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )

    venv = manager.remove("python3.6")

    expected_venv_path = tmp_path / f"{venv_name}-py3.6"
    assert venv.path == expected_venv_path
    assert not expected_venv_path.exists()


def test_remove_by_full_path_to_python(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
) -> None:
    config.merge({"virtualenvs": {"path": str(tmp_path)}})

    (tmp_path / f"{venv_name}-py3.7").mkdir()
    (tmp_path / f"{venv_name}-py3.6").mkdir()

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )

    expected_venv_path = tmp_path / f"{venv_name}-py3.6"
    python_path = expected_venv_path / "bin" / "python"

    venv = manager.remove(str(python_path))

    assert venv.path == expected_venv_path
    assert not expected_venv_path.exists()


def test_remove_raises_if_acting_on_different_project_by_full_path(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
) -> None:
    config.merge({"virtualenvs": {"path": str(tmp_path)}})

    different_venv_name = "different-project"
    different_venv_path = tmp_path / f"{different_venv_name}-py3.6"
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


def test_remove_raises_if_acting_on_different_project_by_name(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
) -> None:
    config.merge({"virtualenvs": {"path": str(tmp_path)}})

    different_venv_name = (
        EnvManager.generate_env_name(
            "different-project",
            str(poetry.file.path.parent),
        )
        + "-py3.6"
    )
    different_venv_path = tmp_path / different_venv_name
    different_venv_bin_path = different_venv_path / "bin"
    different_venv_bin_path.mkdir(parents=True)

    python_path = different_venv_bin_path / "python"
    python_path.touch(exist_ok=True)

    with pytest.raises(IncorrectEnvError):
        manager.remove(different_venv_name)


def test_raises_when_passing_old_env_after_dir_rename(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    venv_name: str,
) -> None:
    # Make sure that poetry raises when trying to remove old venv after you've renamed
    # root directory of the project, which will create another venv with new name.
    # This is not ideal as you still "can't" remove it by name, but it at least doesn't
    # cause any unwanted side effects
    config.merge({"virtualenvs": {"path": str(tmp_path)}})

    previous_venv_name = EnvManager.generate_env_name(
        poetry.package.name,
        "previous_dir_name",
    )
    venv_path = tmp_path / f"{venv_name}-py3.6"
    venv_path.mkdir()

    previous_venv_name = f"{previous_venv_name}-py3.6"
    previous_venv_path = tmp_path / previous_venv_name
    previous_venv_path.mkdir()

    with pytest.raises(IncorrectEnvError):
        manager.remove(previous_venv_name)


def test_remove_also_deactivates(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
) -> None:
    config.merge({"virtualenvs": {"path": str(tmp_path)}})

    (tmp_path / f"{venv_name}-py3.7").mkdir()
    (tmp_path / f"{venv_name}-py3.6").mkdir()

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )

    envs_file = TOMLFile(tmp_path / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.6", "patch": "3.6.6"}
    envs_file.write(doc)

    venv = manager.remove("python3.6")

    expected_venv_path = tmp_path / f"{venv_name}-py3.6"
    assert venv.path == expected_venv_path
    assert not expected_venv_path.exists()

    envs = envs_file.read()
    assert venv_name not in envs


def test_remove_keeps_dir_if_not_deleteable(
    tmp_path: Path,
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    venv_name: str,
) -> None:
    # Ensure we empty rather than delete folder if its is an active mount point.
    # See https://github.com/python-poetry/poetry/pull/2064
    config.merge({"virtualenvs": {"path": str(tmp_path)}})

    venv_path = tmp_path / f"{venv_name}-py3.6"
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

    def err_on_rm_venv_only(path: Path, *args: Any, **kwargs: Any) -> None:
        if path.resolve() == venv_path.resolve():
            raise OSError(16, "Test error")  # ERRNO 16: Device or resource busy
        else:
            remove_directory(path)

    m = mocker.patch(
        "poetry.utils.env.env_manager.remove_directory", side_effect=err_on_rm_venv_only
    )

    venv = manager.remove(f"{venv_name}-py3.6")

    m.assert_any_call(venv_path)

    assert venv_path == venv.path
    assert venv_path.exists()

    assert not folder1_path.exists()
    assert not file1_path.exists()
    assert not file2_path.exists()

    m.side_effect = remove_directory  # Avoid teardown using `err_on_rm_venv_only`


def test_create_venv_tries_to_find_a_compatible_python_executable_using_generic_ones_first(
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    config_virtualenvs_path: Path,
    venv_name: str,
    venv_flags_default: dict[str, bool],
) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    poetry.package.python_versions = "^3.6"

    mocker.patch("sys.version_info", (2, 7, 16))
    mocker.patch("shutil.which", side_effect=lambda py: f"/usr/bin/{py}")
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
        executable=Path("/usr/bin/python3"),
        flags=venv_flags_default,
        prompt="simple-project-py3.7",
    )


def test_create_venv_finds_no_python_executable(
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    config_virtualenvs_path: Path,
    venv_name: str,
) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    poetry.package.python_versions = "^3.6"

    mocker.patch("sys.version_info", (3, 4, 5))
    mocker.patch("shutil.which", return_value=None)

    with pytest.raises(NoCompatiblePythonVersionFound) as e:
        manager.create_venv()

    expected_message = (
        "Poetry was unable to find a compatible version. "
        "If you have one, you can explicitly use it "
        'via the "env use" command.'
    )

    assert str(e.value) == expected_message


def test_create_venv_tries_to_find_a_compatible_python_executable_using_specific_ones(
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    config_virtualenvs_path: Path,
    venv_name: str,
    venv_flags_default: dict[str, bool],
) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    poetry.package.python_versions = "^3.6"

    mocker.patch("sys.version_info", (2, 7, 16))
    mocker.patch("shutil.which", side_effect=lambda py: f"/usr/bin/{py}")
    mocker.patch(
        "subprocess.check_output",
        side_effect=[
            sys.base_prefix,
            "/usr/bin/python3",
            "3.5.3",
            "/usr/bin/python3.9",
            "3.9.0",
            sys.base_prefix,
        ],
    )
    m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=lambda *args, **kwargs: ""
    )

    manager.create_venv()

    m.assert_called_with(
        config_virtualenvs_path / f"{venv_name}-py3.9",
        executable=Path("/usr/bin/python3.9"),
        flags=venv_flags_default,
        prompt="simple-project-py3.9",
    )


def test_create_venv_fails_if_no_compatible_python_version_could_be_found(
    manager: EnvManager, poetry: Poetry, config: Config, mocker: MockerFixture
) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    poetry.package.python_versions = "^4.8"

    mocker.patch("subprocess.check_output", side_effect=[sys.base_prefix])
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
) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    poetry.package.python_versions = "^4.8"

    mocker.patch("subprocess.check_output", side_effect=[sys.base_prefix, "3.8.0"])
    m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=lambda *args, **kwargs: ""
    )

    with pytest.raises(NoCompatiblePythonVersionFound) as e:
        manager.create_venv(executable=Path("python3.8"))

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
    venv_flags_default: dict[str, bool],
) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    version = Version.from_parts(*sys.version_info[:3])
    poetry.package.python_versions = "^" + ".".join(
        str(c) for c in sys.version_info[:3]
    )

    assert version.patch is not None
    mocker.patch("sys.version_info", (version.major, version.minor, version.patch + 1))
    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.9")),
    )
    m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=lambda *args, **kwargs: ""
    )

    manager.create_venv()

    m.assert_called_with(
        config_virtualenvs_path / f"{venv_name}-py{version.major}.{version.minor}",
        executable=None,
        flags=venv_flags_default,
        prompt=f"simple-project-py{version.major}.{version.minor}",
    )


def test_create_venv_uses_patch_version_to_detect_compatibility_with_executable(
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    config_virtualenvs_path: Path,
    venv_name: str,
    venv_flags_default: dict[str, bool],
) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    version = Version.from_parts(*sys.version_info[:3])
    assert version.minor is not None
    poetry.package.python_versions = f"~{version.major}.{version.minor - 1}.0"
    venv_name = manager.generate_env_name(
        "simple-project", str(poetry.file.path.parent)
    )

    check_output = mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(
            Version.parse(f"{version.major}.{version.minor - 1}.0")
        ),
    )
    m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=lambda *args, **kwargs: ""
    )

    manager.create_venv(executable=Path(f"python{version.major}.{version.minor - 1}"))

    assert check_output.called
    m.assert_called_with(
        config_virtualenvs_path / f"{venv_name}-py{version.major}.{version.minor - 1}",
        executable=Path(f"python{version.major}.{version.minor - 1}"),
        flags=venv_flags_default,
        prompt=f"simple-project-py{version.major}.{version.minor - 1}",
    )


def test_create_venv_fails_if_current_python_version_is_not_supported(
    manager: EnvManager, poetry: Poetry
) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    manager.create_venv()

    current_version = Version.parse(".".join(str(c) for c in sys.version_info[:3]))
    assert current_version.minor is not None
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


def test_create_venv_project_name_empty_sets_correct_prompt(
    fixture_dir: FixtureDirGetter,
    project_factory: ProjectFactory,
    config: Config,
    mocker: MockerFixture,
    config_virtualenvs_path: Path,
) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    poetry = project_factory("no", source=fixture_dir("no_name_project"))
    manager = EnvManager(poetry)

    poetry.package.python_versions = "^3.7"
    venv_name = manager.generate_env_name("", str(poetry.file.path.parent))

    mocker.patch("sys.version_info", (2, 7, 16))
    mocker.patch("shutil.which", side_effect=lambda py: f"/usr/bin/{py}")
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
        executable=Path("/usr/bin/python3"),
        flags={
            "always-copy": False,
            "system-site-packages": False,
            "no-pip": False,
            "no-setuptools": False,
        },
        prompt="virtualenv-py3.7",
    )


def test_create_venv_accepts_fallback_version_w_nonzero_patchlevel(
    manager: EnvManager,
    poetry: Poetry,
    config: Config,
    mocker: MockerFixture,
    config_virtualenvs_path: Path,
    venv_name: str,
) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    poetry.package.python_versions = "~3.5.1"

    def mock_check_output(cmd: str, *args: Any, **kwargs: Any) -> str:
        if GET_PYTHON_VERSION_ONELINER in cmd:
            executable = cmd[0]
            if "python3.5" in str(executable):
                return "3.5.12"
            return "3.7.1"

        if GET_BASE_PREFIX in cmd:
            return sys.base_prefix

        return "/usr/bin/python3.5"

    mocker.patch("shutil.which", side_effect=lambda py: f"/usr/bin/{py}")
    check_output = mocker.patch(
        "subprocess.check_output",
        side_effect=mock_check_output,
    )
    m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=lambda *args, **kwargs: ""
    )

    manager.create_venv()

    assert check_output.called
    m.assert_called_with(
        config_virtualenvs_path / f"{venv_name}-py3.5",
        executable=Path("/usr/bin/python3.5"),
        flags={
            "always-copy": False,
            "system-site-packages": False,
            "no-pip": False,
            "no-setuptools": False,
        },
        prompt="simple-project-py3.5",
    )


def test_build_venv_does_not_change_loglevel(
    tmp_path: Path, manager: EnvManager, caplog: LogCaptureFixture
) -> None:
    # see https://github.com/python-poetry/poetry/pull/8760
    venv_path = tmp_path / "venv"
    caplog.set_level(logging.DEBUG)
    manager.build_venv(venv_path)
    assert logging.root.level == logging.DEBUG


@pytest.mark.skipif(sys.platform != "darwin", reason="requires darwin")
def test_venv_backup_exclusion(tmp_path: Path, manager: EnvManager) -> None:
    import xattr

    venv_path = tmp_path / "Virtual Env"

    manager.build_venv(venv_path)

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


def test_generate_env_name_ignores_case_for_case_insensitive_fs(
    poetry: Poetry,
    tmp_path: Path,
) -> None:
    venv_name1 = EnvManager.generate_env_name(poetry.package.name, "MyDiR")
    venv_name2 = EnvManager.generate_env_name(poetry.package.name, "mYdIr")
    if sys.platform == "win32":
        assert venv_name1 == venv_name2
    else:
        assert venv_name1 != venv_name2


def test_generate_env_name_uses_real_path(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    mocker.patch("os.path.realpath", return_value="the_real_dir")
    venv_name1 = EnvManager.generate_env_name("simple-project", "the_real_dir")
    venv_name2 = EnvManager.generate_env_name("simple-project", "linked_dir")
    assert venv_name1 == venv_name2
