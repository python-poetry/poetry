from __future__ import annotations

import os
import subprocess
import sys

import pytest

from poetry.exceptions import PoetryError
from poetry.utils.constants import DEFAULT_REQUESTS_TIMEOUT
from poetry.utils.constants import get_requests_timeout


def test_get_requests_timeout_uses_the_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("POETRY_REQUESTS_TIMEOUT", raising=False)

    assert get_requests_timeout() == DEFAULT_REQUESTS_TIMEOUT


def test_get_requests_timeout_reads_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POETRY_REQUESTS_TIMEOUT", "30")

    assert get_requests_timeout() == 30


def test_get_requests_timeout_reports_a_malformed_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POETRY_REQUESTS_TIMEOUT", "abc")

    with pytest.raises(PoetryError) as e:
        get_requests_timeout()

    assert str(e.value) == "POETRY_REQUESTS_TIMEOUT must be an integer, got 'abc'"


def test_malformed_requests_timeout_does_not_break_unrelated_commands() -> None:
    """
    A malformed POETRY_REQUESTS_TIMEOUT must not break commands that do not
    perform HTTP requests, such as `poetry --version`.
    """
    result = subprocess.run(
        [sys.executable, "-m", "poetry", "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "POETRY_REQUESTS_TIMEOUT": "abc"},
    )

    assert result.returncode == 0, result.stderr
    assert "Poetry (version" in result.stdout
