from __future__ import annotations

import os

import pytest

from tests.helpers import flatten_dict
from tests.helpers import isolated_environment
from tests.helpers import switch_working_directory


def test_flatten_dict() -> None:
    orig_dict = {
        "a": 1,
        "b": 2,
        "c": {
            "x": 8,
            "y": 9,
        },
    }

    flattened_dict = {
        "a": 1,
        "b": 2,
        "c:x": 8,
        "c:y": 9,
    }

    assert flattened_dict == flatten_dict(orig_dict, delimiter=":")


def test_isolated_environment_restores_original_environ() -> None:
    original_environ = dict(os.environ)
    with isolated_environment():
        os.environ["TEST_VAR"] = "test"
    assert os.environ == original_environ


def test_isolated_environment_clears_environ() -> None:
    os.environ["TEST_VAR"] = "test"
    with isolated_environment(clear=True):
        assert "TEST_VAR" not in os.environ
    assert "TEST_VAR" in os.environ


def test_isolated_environment_updates_environ() -> None:
    with isolated_environment(environ={"NEW_VAR": "new_value"}):
        assert os.environ["NEW_VAR"] == "new_value"
    assert "NEW_VAR" not in os.environ


def test_switch_working_directory_restores_original_cwd_on_error(tmp_path) -> None:
    original_cwd = os.getcwd()

    with pytest.raises(RuntimeError):
        with switch_working_directory(tmp_path):
            assert os.getcwd() == str(tmp_path)
            raise RuntimeError("boom")

    assert os.getcwd() == original_cwd


def test_switch_working_directory_remove_deletes_directory(tmp_path) -> None:
    temp_dir = tmp_path / "temp-working-dir"
    temp_dir.mkdir()

    with switch_working_directory(temp_dir, remove=True):
        assert os.getcwd() == str(temp_dir)
        assert temp_dir.exists()

    assert not temp_dir.exists()
