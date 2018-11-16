import os
import shutil
import sys
import tomlkit
from poetry.io import NullIO
from poetry.semver import Version
from poetry.utils._compat import Path
from poetry.utils.env import EnvManager
from poetry.utils.env import VirtualEnv
from poetry.utils.toml_file import TomlFile


def test_virtualenvs_with_spaces_in_their_path_work_as_expected(tmp_dir, config):
    venv_path = Path(tmp_dir) / "Virtual Env"

    EnvManager(config).build_venv(str(venv_path))

    venv = VirtualEnv(venv_path)

    assert venv.run("python", "-V", shell=True).startswith("Python")


def test_env_get_in_project_venv(tmp_dir, environ, config):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    (Path(tmp_dir) / ".venv").mkdir()

    venv = EnvManager(config).get(Path(tmp_dir))

    assert venv.path == Path(tmp_dir) / ".venv"


CWD = Path(__file__).parent.parent / "fixtures" / "simple_project"


def build_venv(path, executable=None):
    os.mkdir(path)


def remove_venv(path):
    shutil.rmtree(path)


def test_activate_activates_non_existing_virtualenv_no_envs_file(
    tmp_dir, config, mocker, environ
):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    config.add_property("settings.virtualenvs.path", str(tmp_dir))

    mocker.patch("subprocess.check_output", side_effect=["3.7.1", "3.7"])
    mocker.patch(
        "subprocess.Popen.communicate",
        side_effect=[("/prefix", None), ("/prefix", None)],
    )
    m = mocker.patch("poetry.utils.env.EnvManager.build_venv", side_effect=build_venv)

    env = EnvManager(config).activate("python3.7", CWD, NullIO())

    m.assert_called_with(
        os.path.join(tmp_dir, "simple_project-py3.7"), executable="python3.7"
    )

    envs_file = TomlFile(Path(tmp_dir) / "envs.toml")
    assert envs_file.exists()
    envs = envs_file.read()
    assert envs["simple_project"]["minor"] == "3.7"
    assert envs["simple_project"]["patch"] == "3.7.1"

    assert env.path == Path(tmp_dir) / "simple_project-py3.7"
    assert env.base == Path("/prefix")


def test_activate_activates_existing_virtualenv_no_envs_file(
    tmp_dir, config, mocker, environ
):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    os.mkdir(os.path.join(tmp_dir, "simple_project-py3.7"))

    config.add_property("settings.virtualenvs.path", str(tmp_dir))

    mocker.patch("subprocess.check_output", side_effect=["3.7.1"])
    mocker.patch("subprocess.Popen.communicate", side_effect=[("/prefix", None)])
    m = mocker.patch("poetry.utils.env.EnvManager.build_venv", side_effect=build_venv)

    env = EnvManager(config).activate("python3.7", CWD, NullIO())

    m.assert_not_called()

    envs_file = TomlFile(Path(tmp_dir) / "envs.toml")
    assert envs_file.exists()
    envs = envs_file.read()
    assert envs["simple_project"]["minor"] == "3.7"
    assert envs["simple_project"]["patch"] == "3.7.1"

    assert env.path == Path(tmp_dir) / "simple_project-py3.7"
    assert env.base == Path("/prefix")


def test_activate_activates_same_virtualenv_with_envs_file(
    tmp_dir, config, mocker, environ
):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    envs_file = TomlFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc["simple_project"] = {"minor": "3.7", "patch": "3.7.1"}
    envs_file.write(doc)

    os.mkdir(os.path.join(tmp_dir, "simple_project-py3.7"))

    config.add_property("settings.virtualenvs.path", str(tmp_dir))

    mocker.patch("subprocess.check_output", side_effect=["3.7.1"])
    mocker.patch("subprocess.Popen.communicate", side_effect=[("/prefix", None)])
    m = mocker.patch("poetry.utils.env.EnvManager.create_venv")

    env = EnvManager(config).activate("python3.7", CWD, NullIO())

    m.assert_not_called()

    assert envs_file.exists()
    envs = envs_file.read()
    assert envs["simple_project"]["minor"] == "3.7"
    assert envs["simple_project"]["patch"] == "3.7.1"

    assert env.path == Path(tmp_dir) / "simple_project-py3.7"
    assert env.base == Path("/prefix")


def test_activate_activates_different_virtualenv_with_envs_file(
    tmp_dir, config, mocker, environ
):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    envs_file = TomlFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc["simple_project"] = {"minor": "3.7", "patch": "3.7.1"}
    envs_file.write(doc)

    os.mkdir(os.path.join(tmp_dir, "simple_project-py3.7"))

    config.add_property("settings.virtualenvs.path", str(tmp_dir))

    mocker.patch("subprocess.check_output", side_effect=["3.6.6", "3.6", "3.6"])
    mocker.patch(
        "subprocess.Popen.communicate",
        side_effect=[("/prefix", None), ("/prefix", None), ("/prefix", None)],
    )
    m = mocker.patch("poetry.utils.env.EnvManager.build_venv", side_effect=build_venv)

    env = EnvManager(config).activate("python3.6", CWD, NullIO())

    m.assert_called_with(
        os.path.join(tmp_dir, "simple_project-py3.6"), executable="python3.6"
    )

    assert envs_file.exists()
    envs = envs_file.read()
    assert envs["simple_project"]["minor"] == "3.6"
    assert envs["simple_project"]["patch"] == "3.6.6"

    assert env.path == Path(tmp_dir) / "simple_project-py3.6"
    assert env.base == Path("/prefix")


def test_activate_activates_recreates_for_different_minor(
    tmp_dir, config, mocker, environ
):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    envs_file = TomlFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc["simple_project"] = {"minor": "3.7", "patch": "3.7.0"}
    envs_file.write(doc)

    os.mkdir(os.path.join(tmp_dir, "simple_project-py3.7"))

    config.add_property("settings.virtualenvs.path", str(tmp_dir))

    mocker.patch("subprocess.check_output", side_effect=["3.7.1", "3.7", "3.7"])
    mocker.patch(
        "subprocess.Popen.communicate",
        side_effect=[("/prefix", None), ("/prefix", None), ("/prefix", None)],
    )
    build_venv_m = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=build_venv
    )
    remove_venv_m = mocker.patch(
        "poetry.utils.env.EnvManager.remove_venv", side_effect=remove_venv
    )

    env = EnvManager(config).activate("python3.7", CWD, NullIO())

    build_venv_m.assert_called_with(
        os.path.join(tmp_dir, "simple_project-py3.7"), executable="python3.7"
    )
    remove_venv_m.assert_called_with(os.path.join(tmp_dir, "simple_project-py3.7"))

    assert envs_file.exists()
    envs = envs_file.read()
    assert envs["simple_project"]["minor"] == "3.7"
    assert envs["simple_project"]["patch"] == "3.7.1"

    assert env.path == Path(tmp_dir) / "simple_project-py3.7"
    assert env.base == Path("/prefix")
    assert (Path(tmp_dir) / "simple_project-py3.7").exists()


def test_deactivate_non_activated_but_existing(tmp_dir, config, mocker, environ):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    (
        Path(tmp_dir)
        / "simple_project-py{}".format(".".join(str(c) for c in sys.version_info[:2]))
    ).mkdir()

    config.add_property("settings.virtualenvs.path", str(tmp_dir))

    mocker.patch("subprocess.check_output", side_effect=["/prefix", "/prefix"])

    EnvManager(config).deactivate(CWD, NullIO())
    env = EnvManager(config).get(CWD)

    assert env.path == Path(tmp_dir) / "simple_project-py{}".format(
        ".".join(str(c) for c in sys.version_info[:2])
    )
    assert Path("/prefix")


def test_deactivate_activated(tmp_dir, config, mocker, environ):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    version = Version.parse(".".join(str(c) for c in sys.version_info[:3]))
    other_version = Version.parse("3.4") if version.major == 2 else version.next_minor
    (
        Path(tmp_dir) / "simple_project-py{}.{}".format(version.major, version.minor)
    ).mkdir()
    (
        Path(tmp_dir)
        / "simple_project-py{}.{}".format(other_version.major, other_version.minor)
    ).mkdir()

    envs_file = TomlFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc["simple_project"] = {
        "minor": "{}.{}".format(other_version.major, other_version.minor),
        "patch": other_version.text,
    }
    envs_file.write(doc)

    config.add_property("settings.virtualenvs.path", str(tmp_dir))

    mocker.patch("subprocess.check_output", side_effect=["/prefix", "/prefix"])

    EnvManager(config).deactivate(CWD, NullIO())
    env = EnvManager(config).get(CWD)

    assert env.path == Path(tmp_dir) / "simple_project-py{}.{}".format(
        version.major, version.minor
    )
    assert Path("/prefix")

    envs = envs_file.read()
    assert len(envs) == 0


def test_get_prefers_explicitly_activated_virtualenvs_over_env_var(
    tmp_dir, config, mocker, environ
):
    environ["VIRTUAL_ENV"] = "/environment/prefix"

    config.add_property("settings.virtualenvs.path", str(tmp_dir))
    (Path(tmp_dir) / "simple_project-py3.7").mkdir()

    envs_file = TomlFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc["simple_project"] = {"minor": "3.7", "patch": "3.7.0"}
    envs_file.write(doc)

    mocker.patch("subprocess.Popen.communicate", side_effect=[("/prefix", None)])

    env = EnvManager(config).get(CWD)

    assert env.path == Path(tmp_dir) / "simple_project-py3.7"
    assert env.base == Path("/prefix")
