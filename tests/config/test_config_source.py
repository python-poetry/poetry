from __future__ import annotations

from copy import deepcopy

import pytest

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


@pytest.mark.parametrize(
    ("migration", "expected_result", "expected_output"),
    [
        pytest.param(
            ConfigSourceMigration(
                old_key="virtualenvs.prefer-active-python",
                new_key="virtualenvs.use-poetry-python",
            ),
            True,
            "virtualenvs.prefer-active-python = true -> "
            "virtualenvs.use-poetry-python = true",
            id="rename-key",
        ),
        pytest.param(
            ConfigSourceMigration(
                old_key="virtualenvs.prefer-active-python",
                new_key=None,
            ),
            True,
            "virtualenvs.prefer-active-python = true -> Removed from config",
            id="remove-key",
        ),
        pytest.param(
            ConfigSourceMigration(
                old_key="virtualenvs.prefer-active-python",
                new_key="virtualenvs.use-poetry-python",
                value_migration={True: UNSET, False: True},
            ),
            True,
            "virtualenvs.prefer-active-python = true -> "
            "virtualenvs.use-poetry-python = Not explicit set",
            id="unset-value",
        ),
        pytest.param(
            ConfigSourceMigration(
                old_key="virtualenvs.missing-key",
                new_key="virtualenvs.use-poetry-python",
            ),
            False,
            "",
            id="missing-key",
        ),
    ],
)
def test_config_source_migration_dry_run(
    migration: ConfigSourceMigration,
    expected_result: bool,
    expected_output: str,
) -> None:
    config_source = make_config_source()
    original_config = deepcopy(config_source._config)
    io = BufferedIO()

    assert migration.dry_run(config_source, io) is expected_result
    assert io.fetch_output().strip() == expected_output
    assert config_source._config == original_config
