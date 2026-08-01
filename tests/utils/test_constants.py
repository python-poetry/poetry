from __future__ import annotations

import os

from typing import TYPE_CHECKING

import pytest

from poetry.utils.constants import REQUESTS_TIMEOUT
from poetry.utils.constants import _reset_requests_timeout_cache
from poetry.utils.constants import get_requests_timeout


if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def requests_timeout_cache() -> Iterator[None]:
    _reset_requests_timeout_cache()
    yield
    _reset_requests_timeout_cache()


def test_get_requests_timeout_defaults_to_constant(environ: None) -> None:
    assert get_requests_timeout() == REQUESTS_TIMEOUT


def test_get_requests_timeout_from_environment(environ: None) -> None:
    os.environ["POETRY_REQUESTS_TIMEOUT"] = "60"

    assert get_requests_timeout() == 60


def test_get_requests_timeout_reports_invalid_environment_value(
    environ: None,
) -> None:
    os.environ["POETRY_REQUESTS_TIMEOUT"] = "abc"

    with pytest.raises(ValueError, match="POETRY_REQUESTS_TIMEOUT"):
        get_requests_timeout()


def test_get_requests_timeout_caches_environment_value(environ: None) -> None:
    os.environ["POETRY_REQUESTS_TIMEOUT"] = "60"

    assert get_requests_timeout() == 60

    os.environ["POETRY_REQUESTS_TIMEOUT"] = "90"

    assert get_requests_timeout() == 60


def test_get_requests_timeout_caches_invalid_environment_value(environ: None) -> None:
    os.environ["POETRY_REQUESTS_TIMEOUT"] = "abc"

    with pytest.raises(ValueError, match="POETRY_REQUESTS_TIMEOUT"):
        get_requests_timeout()

    os.environ["POETRY_REQUESTS_TIMEOUT"] = "60"

    with pytest.raises(ValueError, match="POETRY_REQUESTS_TIMEOUT"):
        get_requests_timeout()
