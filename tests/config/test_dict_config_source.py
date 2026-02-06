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


def test_dict_config_source_escaped_dot_key() -> None:
    config_source = DictConfigSource()

    config_source.add_property("repositories.foo\\.bar.url", "https://example.com/simple")
    assert config_source._config == {
        "repositories": {"foo.bar": {"url": "https://example.com/simple"}}
    }

    assert (
        config_source.get_property("repositories.foo\\.bar.url")
        == "https://example.com/simple"
    )

    config_source.remove_property("repositories.foo\\.bar.url")
    assert config_source._config == {"repositories": {"foo.bar": {}}}
