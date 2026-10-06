from __future__ import annotations

import sys

from typing import TYPE_CHECKING

import pytest
import tomlkit

from poetry.config.config_source import PropertyNotFoundError
from poetry.config.file_config_source import FileConfigSource
from poetry.toml import TOMLFile


if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture
    from tomlkit.toml_document import TOMLDocument


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


def test_file_config_source_add_property_with_list_keys(tmp_path: Path) -> None:
    """Repository names containing periods should be stored correctly."""
    config = tmp_path.joinpath("config.toml")
    config.touch()

    config_source = FileConfigSource(TOMLFile(config))

    config_source.add_property(
        ["repositories", "my.repo", "url"],
        "https://example.com/simple/",
    )
    data = config_source._file.read()
    repos = data["repositories"]
    assert repos["my.repo"]["url"] == "https://example.com/simple/"


def test_file_config_source_get_property_with_list_keys(tmp_path: Path) -> None:
    """Repository names containing periods should be retrievable via list keys."""
    config = tmp_path.joinpath("config.toml")
    with config.open(mode="w", encoding="utf-8") as f:
        f.write(
            '[repositories]\n[repositories."my.repo"]\nurl = "https://example.com/simple/"\n'
        )

    config_source = FileConfigSource(TOMLFile(config))

    assert config_source.get_property(["repositories", "my.repo", "url"]) == (
        "https://example.com/simple/"
    )


def test_file_config_source_remove_property_with_list_keys(
    tmp_path: Path,
) -> None:
    """Repository names containing periods should be removable via list keys."""
    config = tmp_path.joinpath("config.toml")
    with config.open(mode="w", encoding="utf-8") as f:
        f.write(
            "[repositories]\n"
            '[repositories."my.repo"]\nurl = "https://example.com/simple/"\n'
            '[repositories.other]\nurl = "https://other.com/simple/"\n'
        )

    config_source = FileConfigSource(TOMLFile(config))

    config_source.remove_property(["repositories", "my.repo"])
    data = config_source._file.read()
    repos = data.get("repositories", {})
    assert "my.repo" not in repos
    other = data["repositories"]
    assert other["other"]["url"] == "https://other.com/simple/"


def test_file_config_source_name(tmp_path: Path) -> None:
    config = tmp_path.joinpath("config.toml")
    config.touch()

    config_source = FileConfigSource(TOMLFile(config))

    assert config_source.name == str(config)


def test_file_config_source_remove_missing_property_is_noop(tmp_path: Path) -> None:
    config_data = {"system-git-client": True}

    config = tmp_path.joinpath("config.toml")
    with config.open(mode="w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(config_data))

    config_source = FileConfigSource(TOMLFile(config))

    original_file = config.read_bytes()

    config_source.remove_property("virtualenvs.use-poetry-python")

    assert config.read_bytes() == original_file


def test_file_config_source_add_property_creates_missing_file(tmp_path: Path) -> None:
    config = tmp_path.joinpath("config.toml")
    assert not config.exists()

    config_source = FileConfigSource(TOMLFile(config))

    config_source.add_property("virtualenvs.create", False)

    assert config.exists()
    assert config_source._file.read() == {"virtualenvs": {"create": False}}


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="permission bits are not meaningful on Windows",
)
def test_file_config_source_creates_file_with_owner_only_permissions(
    tmp_path: Path,
) -> None:
    config = tmp_path.joinpath("config.toml")
    assert not config.exists()

    config_source = FileConfigSource(TOMLFile(config))

    config_source.add_property("system-git-client", True)

    assert config.exists()
    assert config.stat().st_mode & 0o077 == 0


def test_file_config_source_rolls_back_on_write_failure(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    config_data = {"system-git-client": True}

    config = tmp_path.joinpath("config.toml")
    with config.open(mode="w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(config_data))

    config_source = FileConfigSource(TOMLFile(config))

    real_write = config_source.file.write
    calls: list[int] = []

    def flaky_write(data: TOMLDocument) -> None:
        calls.append(1)
        if len(calls) == 1:
            raise OSError("disk full")
        real_write(data)

    write = mocker.patch.object(config_source.file, "write", side_effect=flaky_write)

    with pytest.raises(OSError, match="disk full"):
        config_source.add_property("system-git-client", False)

    assert write.call_count == 2
    assert write.call_args_list[0].args[0] == {"system-git-client": False}
    assert write.call_args_list[1].args[0] == config_data
    assert config_source.file.read() == config_data
