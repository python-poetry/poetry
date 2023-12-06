from __future__ import annotations

import re

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from urllib.parse import urlparse

import pytest


if TYPE_CHECKING:
    from httpretty import httpretty
    from httpretty.core import HTTPrettyRequest

    from tests.types import FixtureDirGetter


@pytest.fixture
def mock_file_downloads(http: type[httpretty], fixture_dir: FixtureDirGetter) -> None:
    def callback(
        request: HTTPrettyRequest, uri: str, headers: dict[str, Any]
    ) -> list[int | dict[str, Any] | bytes]:
        name = Path(urlparse(uri).path).name

        fixture = Path(__file__).parent.parent.joinpath(
            "repositories/fixtures/pypi.org/dists/" + name
        )

        if not fixture.exists():
            fixture = fixture_dir("distributions") / name

            if not fixture.exists():
                fixture = (
                    fixture_dir("distributions") / "demo-0.1.0-py2.py3-none-any.whl"
                )

        return [200, headers, fixture.read_bytes()]

    http.register_uri(
        http.GET,
        re.compile("^https://files.pythonhosted.org/.*$"),
        body=callback,
    )
