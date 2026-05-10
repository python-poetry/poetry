from __future__ import annotations

import re

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import pytest
import responses


if TYPE_CHECKING:
    from collections.abc import Iterator

    from requests import PreparedRequest

    from tests.types import HttpResponse
    from tests.types import PythonHostedFileMocker


@pytest.fixture
def mock_files_python_hosted_factory(
    http: responses.RequestsMock,
) -> PythonHostedFileMocker:
    def factory(
        distribution_locations: list[Path], metadata_locations: list[Path]
    ) -> None:
        def file_callback(request: PreparedRequest) -> HttpResponse:
            assert request.url
            name = Path(urlparse(request.url).path).name

            locations = (
                metadata_locations
                if name.endswith(".metadata")
                else distribution_locations
            )

            for location in locations:
                fixture = location / name
                if fixture.exists():
                    return 200, {}, fixture.read_bytes()

            return 404, {}, b"Not Found"

        def mock_file_callback(request: PreparedRequest) -> HttpResponse:
            return 200, {}, b""

        http.add_callback(
            responses.GET,
            re.compile(r"^https://files\.pythonhosted\.org/.*$"),
            callback=file_callback,
        )

        http.add_callback(
            responses.GET,
            re.compile(r"^https://mock\.pythonhosted\.org/.*$"),
            callback=mock_file_callback,
        )

    return factory


@pytest.fixture
def mock_files_python_hosted(
    mock_files_python_hosted_factory: PythonHostedFileMocker,
    package_distribution_locations: list[Path],
    package_metadata_locations: list[Path],
) -> Iterator[None]:
    mock_files_python_hosted_factory(
        distribution_locations=package_distribution_locations,
        metadata_locations=package_metadata_locations,
    )
    yield None
