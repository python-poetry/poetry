from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    import httpretty


@pytest.fixture(autouse=True)
def disable_httpretty(http: type[httpretty.httpretty]) -> None:
    http.disable()
