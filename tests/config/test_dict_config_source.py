from __future__ import annotations

import pytest

from poetry.config.config_source import PropertyNotFoundError
from poetry.config.dict_config_source import DictConfigSource


def test_dict_config_source_add_property() -> None:
    config_source = DictConfigSource()
    assert config_source._config == {}

    config_source.add_property("system-git-client", True)
    assert config_source._config == {"system-git-client": True}

    config_source.add_property("virtualenvs.use-poetry-python", False)
    assert config_source._config == {
        "virtualenvs": {
            "use-poetry-python": False,
        },
        "system-git-client": True,
    }


def test_dict_config_source_remove_property() -> None:
    config_data = {
        "virtualenvs": {
            "use-poetry-python": False,
        },
        "system-git-client": True,
    }

    config_source = DictConfigSource()
    config_source._config = config_data

    config_source.remove_property("system-git-client")
    assert config_source._config == {
        "virtualenvs": {
            "use-poetry-python": False,
        }
    }

    config_source.remove_property("virtualenvs.use-poetry-python")
    assert config_source._config == {"virtualenvs": {}}


def test_dict_config_source_get_property() -> None:
    config_data = {
        "virtualenvs": {
            "use-poetry-python": False,
        },
        "system-git-client": True,
    }

    config_source = DictConfigSource()
    config_source._config = config_data

    assert config_source.get_property("virtualenvs.use-poetry-python") is False
    assert config_source.get_property("system-git-client") is True


def test_dict_config_source_get_property_should_raise_if_not_found() -> None:
    config_source = DictConfigSource()

    with pytest.raises(
        PropertyNotFoundError, match=r"Key virtualenvs\.use-poetry-python not in config"
    ):
        _ = config_source.get_property("virtualenvs.use-poetry-python")


def test_dict_config_source_add_property_with_list_keys() -> None:
    """Repository names containing periods should be preserved as a single key."""
    config_source = DictConfigSource()

    config_source.add_property(["http-basic", "my.repo"], {"username": "user"})
    assert config_source._config == {
        "http-basic": {
            "my.repo": {"username": "user"},
        },
    }


def test_dict_config_source_get_property_with_list_keys() -> None:
    """Repository names containing periods should be retrievable via list keys."""
    config_source = DictConfigSource()
    config_source._config = {
        "http-basic": {
            "my.repo": {"username": "user", "password": "pass"},
        },
    }

    assert config_source.get_property(["http-basic", "my.repo"]) == {
        "username": "user",
        "password": "pass",
    }
    assert config_source.get_property(["http-basic", "my.repo", "username"]) == "user"


def test_dict_config_source_remove_property_with_list_keys() -> None:
    """Repository names containing periods should be removable via list keys."""
    config_source = DictConfigSource()
    config_source._config = {
        "http-basic": {
            "my.repo": {"username": "user"},
            "other": {"username": "other"},
        },
    }

    config_source.remove_property(["http-basic", "my.repo"])
    assert config_source._config == {
        "http-basic": {
            "other": {"username": "other"},
        },
    }


def test_dict_config_source_add_property_with_periods_in_repo_name() -> None:
    """Verifies that using list keys does not split on periods in repo name."""
    config_source = DictConfigSource()

    # Using list keys: "my.repo" stays as a single key
    config_source.add_property(
        ["repositories", "my.repo", "url"],
        "https://example.com/simple/",
    )
    assert config_source._config == {
        "repositories": {
            "my.repo": {"url": "https://example.com/simple/"},
        },
    }

    # Contrast: using dotted string would incorrectly split "my.repo"
    config_source2 = DictConfigSource()
    config_source2.add_property(
        "repositories.my.repo.url",
        "https://example.com/simple/",
    )
    # The dotted string splits "my.repo" into two keys, which is the bug
    assert config_source2._config == {
        "repositories": {
            "my": {"repo": {"url": "https://example.com/simple/"}},
        },
    }
