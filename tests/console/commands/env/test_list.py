import tomlkit

from cleo.testers import CommandTester

from poetry.utils._compat import Path
from poetry.utils.env import EnvManager
from poetry.utils.toml_file import TomlFile


def test_none_activated(app, tmp_dir, config):
    app.poetry._config = config

    config.add_property("settings.virtualenvs.path", str(tmp_dir))

    venv_name = EnvManager.generate_env_name(
        "simple_project", str(app.poetry.file.parent)
    )
    (Path(tmp_dir) / "{}-py3.7".format(venv_name)).mkdir()
    (Path(tmp_dir) / "{}-py3.6".format(venv_name)).mkdir()

    command = app.find("env list")
    tester = CommandTester(command)
    tester.execute()

    expected = """\
{}-py3.6
{}-py3.7
""".format(
        venv_name, venv_name
    )

    assert expected == tester.io.fetch_output()


def test_activated(app, tmp_dir, config):
    app.poetry._config = config

    config.add_property("settings.virtualenvs.path", str(tmp_dir))

    venv_name = EnvManager.generate_env_name(
        "simple_project", str(app.poetry.file.parent)
    )
    (Path(tmp_dir) / "{}-py3.7".format(venv_name)).mkdir()
    (Path(tmp_dir) / "{}-py3.6".format(venv_name)).mkdir()

    envs_file = TomlFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.0"}
    envs_file.write(doc)

    command = app.find("env list")
    tester = CommandTester(command)
    tester.execute()

    expected = """\
{}-py3.6
{}-py3.7 (Activated)
""".format(
        venv_name, venv_name
    )

    assert expected == tester.io.fetch_output()
