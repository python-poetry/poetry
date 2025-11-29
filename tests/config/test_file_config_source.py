from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import tomlkit

from poetry.config.config_source import PropertyNotFoundError
from poetry.config.file_config_source import FileConfigSource
from poetry.toml import TOMLFile


if TYPE_CHECKING:
    from pathlib import Path


def test_file_config_source_add_property(tmp_path: Path) -> None:
    config = tmp_path.joinpath("config.toml")
    config.touch()

    config_source = FileConfigSource(TOMLFile(config))

    assert config_source._file.read() == {}

    config_source.add_property("system-git-client", True)
    assert config_source._file.read() == {"system-git-client": True}

    config_source.add_property("virtualenvs.use-poetry-python", False)
    assert config_source._file.read() == {
        "virtualenvs": {
            "use-poetry-python": False,
        },
        "system-git-client": True,
    }


def test_file_config_source_remove_property(tmp_path: Path) -> None:
    config_data = {
        "virtualenvs": {
            "use-poetry-python": False,
        },
        "system-git-client": True,
    }

    config = tmp_path.joinpath("config.toml")
    with config.open(mode="w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(config_data))

    config_source = FileConfigSource(TOMLFile(config))

    config_source.remove_property("system-git-client")
    assert config_source._file.read() == {
        "virtualenvs": {
            "use-poetry-python": False,
        }
    }

    config_source.remove_property("virtualenvs.use-poetry-python")
    assert config_source._file.read() == {}


def test_file_config_source_get_property(tmp_path: Path) -> None:
    config_data = {
        "virtualenvs": {
            "use-poetry-python": False,
        },
        "system-git-client": True,
    }

    config = tmp_path.joinpath("config.toml")
    with config.open(mode="w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(config_data))

    config_source = FileConfigSource(TOMLFile(config))

    assert config_source.get_property("virtualenvs.use-poetry-python") is False
    assert config_source.get_property("system-git-client") is True


def test_file_config_source_get_property_should_raise_if_not_found(
    tmp_path: Path,
) -> None:
    config = tmp_path.joinpath("config.toml")
    config.touch()

    config_source = FileConfigSource(TOMLFile(config))

    with pytest.raises(
        PropertyNotFoundError, match=r"Key virtualenvs\.use-poetry-python not in config"
    ):
        _ = config_source.get_property("virtualenvs.use-poetry-python")
