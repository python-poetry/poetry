from __future__ import annotations

from copy import deepcopy

from cleo.io.buffered_io import BufferedIO

from poetry.config.config_source import UNSET
from poetry.config.config_source import ConfigSourceMigration
from poetry.config.dict_config_source import DictConfigSource


def make_config_source() -> DictConfigSource:
    config_source = DictConfigSource()
    config_source._config = {
        "virtualenvs": {
            "prefer-active-python": True,
        },
        "system-git-client": True,
    }

    return config_source


def test_config_source_migration_rename_key() -> None:
    config_source = make_config_source()

    migration = ConfigSourceMigration(
        old_key="virtualenvs.prefer-active-python",
        new_key="virtualenvs.use-poetry-python",
    )

    migration.apply(config_source)

    assert config_source._config == {
        "virtualenvs": {
            "use-poetry-python": True,
        },
        "system-git-client": True,
    }


def test_config_source_migration_remove_key() -> None:
    config_source = make_config_source()

    migration = ConfigSourceMigration(
        old_key="virtualenvs.prefer-active-python",
        new_key=None,
    )

    migration.apply(config_source)

    assert config_source._config == {
        "virtualenvs": {},
        "system-git-client": True,
    }


def test_config_source_migration_unset_value() -> None:
    config_source = make_config_source()

    migration = ConfigSourceMigration(
        old_key="virtualenvs.prefer-active-python",
        new_key="virtualenvs.use-poetry-python",
        value_migration={True: UNSET, False: True},
    )

    migration.apply(config_source)

    assert config_source._config == {
        "virtualenvs": {},
        "system-git-client": True,
    }


def test_config_source_migration_complex_migration() -> None:
    config_source = make_config_source()

    migration = ConfigSourceMigration(
        old_key="virtualenvs.prefer-active-python",
        new_key="virtualenvs.use-poetry-python",
        value_migration={True: None, False: True},
    )

    migration.apply(config_source)

    assert config_source._config == {
        "virtualenvs": {
            "use-poetry-python": None,
        },
        "system-git-client": True,
    }


def test_config_source_migration_dry_run_rename_key() -> None:
    config_source = make_config_source()
    original_config = deepcopy(config_source._config)
    io = BufferedIO()

    migration = ConfigSourceMigration(
        old_key="virtualenvs.prefer-active-python",
        new_key="virtualenvs.use-poetry-python",
    )

    assert migration.dry_run(config_source, io) is True
    assert (
        io.fetch_output() == "virtualenvs.prefer-active-python = true -> "
        "virtualenvs.use-poetry-python = true\n"
    )
    assert config_source._config == original_config


def test_config_source_migration_dry_run_remove_key() -> None:
    config_source = make_config_source()
    original_config = deepcopy(config_source._config)
    io = BufferedIO()

    migration = ConfigSourceMigration(
        old_key="virtualenvs.prefer-active-python",
        new_key=None,
    )

    assert migration.dry_run(config_source, io) is True
    assert (
        io.fetch_output()
        == "virtualenvs.prefer-active-python = true -> Removed from config\n"
    )
    assert config_source._config == original_config


def test_config_source_migration_dry_run_unset_value() -> None:
    config_source = make_config_source()
    original_config = deepcopy(config_source._config)
    io = BufferedIO()

    migration = ConfigSourceMigration(
        old_key="virtualenvs.prefer-active-python",
        new_key="virtualenvs.use-poetry-python",
        value_migration={True: UNSET, False: True},
    )

    assert migration.dry_run(config_source, io) is True
    assert (
        io.fetch_output() == "virtualenvs.prefer-active-python = true -> "
        "virtualenvs.use-poetry-python = Not explicit set\n"
    )
    assert config_source._config == original_config


def test_config_source_migration_dry_run_missing_key() -> None:
    config_source = make_config_source()
    original_config = deepcopy(config_source._config)
    io = BufferedIO()

    migration = ConfigSourceMigration(
        old_key="virtualenvs.missing-key",
        new_key="virtualenvs.use-poetry-python",
    )

    assert migration.dry_run(config_source, io) is False
    assert io.fetch_output() == ""
    assert config_source._config == original_config
