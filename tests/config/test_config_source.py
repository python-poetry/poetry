from __future__ import annotations

from poetry.config.config_source import UNSET
from poetry.config.config_source import ConfigSourceMigration
from poetry.config.dict_config_source import DictConfigSource


def test_config_source_migration_rename_key() -> None:
    config_data = {
        "virtualenvs": {
            "prefer-active-python": True,
        },
        "system-git-client": True,
    }

    config_source = DictConfigSource()
    config_source._config = config_data

    migration = ConfigSourceMigration(
        old_key="virtualenvs.prefer-active-python",
        new_key="virtualenvs.use-poetry-python",
    )

    migration.apply(config_source)

    config_source._config = {
        "virtualenvs": {
            "use-poetry-python": True,
        },
        "system-git-client": True,
    }


def test_config_source_migration_remove_key() -> None:
    config_data = {
        "virtualenvs": {
            "prefer-active-python": True,
        },
        "system-git-client": True,
    }

    config_source = DictConfigSource()
    config_source._config = config_data

    migration = ConfigSourceMigration(
        old_key="virtualenvs.prefer-active-python",
        new_key=None,
    )

    migration.apply(config_source)

    config_source._config = {
        "virtualenvs": {},
        "system-git-client": True,
    }


def test_config_source_migration_unset_value() -> None:
    config_data = {
        "virtualenvs": {
            "prefer-active-python": True,
        },
        "system-git-client": True,
    }

    config_source = DictConfigSource()
    config_source._config = config_data

    migration = ConfigSourceMigration(
        old_key="virtualenvs.prefer-active-python",
        new_key="virtualenvs.use-poetry-python",
        value_migration={True: UNSET, False: True},
    )

    migration.apply(config_source)

    config_source._config = {
        "virtualenvs": {},
        "system-git-client": True,
    }


def test_config_source_migration_complex_migration() -> None:
    config_data = {
        "virtualenvs": {
            "prefer-active-python": True,
        },
        "system-git-client": True,
    }

    config_source = DictConfigSource()
    config_source._config = config_data

    migration = ConfigSourceMigration(
        old_key="virtualenvs.prefer-active-python",
        new_key="virtualenvs.use-poetry-python",
        value_migration={True: None, False: True},
    )

    migration.apply(config_source)

    config_source._config = {
        "virtualenvs": {
            "use-poetry-python": None,
        },
        "system-git-client": True,
    }
