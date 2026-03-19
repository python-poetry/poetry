from __future__ import annotations

import os

from typing import TYPE_CHECKING

import pytest

from tests.helpers import flatten_dict
from tests.helpers import isolated_environment
from tests.helpers import switch_working_directory


if TYPE_CHECKING:
    from pathlib import Path


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


@pytest.mark.parametrize(
    ("remove", "raise_error"),
    [(False, False), (False, True), (True, False), (True, True)],
)
def test_switch_working_directory_changes_restores_and_removes(
    tmp_path: Path, remove: bool, raise_error: bool
) -> None:
    original_cwd = os.getcwd()
    temp_dir = tmp_path / f"temp-working-dir-{remove}-{raise_error}"
    temp_dir.mkdir()

    if raise_error:
        with (
            pytest.raises(RuntimeError),
            switch_working_directory(temp_dir, remove=remove),
        ):
            assert os.getcwd() == str(temp_dir)
            raise RuntimeError("boom")
    else:
        with switch_working_directory(temp_dir, remove=remove):
            assert os.getcwd() == str(temp_dir)

    assert os.getcwd() == original_cwd
    assert temp_dir.exists() is (not remove)
