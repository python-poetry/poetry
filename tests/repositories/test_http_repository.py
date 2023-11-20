from __future__ import annotations

import shutil

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from zipfile import ZipFile

import pytest

from packaging.metadata import parse_email
from poetry.core.packages.utils.link import Link

from poetry.inspection.lazy_wheel import HTTPRangeRequestUnsupported
from poetry.repositories.http_repository import HTTPRepository
from poetry.utils.helpers import HTTPRangeRequestSupported


if TYPE_CHECKING:
    from packaging.utils import NormalizedName
    from poetry.core.constraints.version import Version
    from pytest_mock import MockerFixture


class MockRepository(HTTPRepository):
    DIST_FIXTURES = Path(__file__).parent / "fixtures" / "pypi.org" / "dists"

    def __init__(self, lazy_wheel: bool = True) -> None:
        super().__init__("foo", "https://foo.com")
        self._lazy_wheel = lazy_wheel

    def _get_release_info(
        self, name: NormalizedName, version: Version
    ) -> dict[str, Any]:
        raise NotImplementedError


@pytest.mark.parametrize("lazy_wheel", [False, True])
@pytest.mark.parametrize("supports_range_requests", [None, False, True])
def test_get_info_from_wheel(
    mocker: MockerFixture, lazy_wheel: bool, supports_range_requests: bool | None
) -> None:
    filename = "poetry_core-1.5.0-py3-none-any.whl"
    filepath = MockRepository.DIST_FIXTURES / filename
    with ZipFile(filepath) as zf:
        metadata, _ = parse_email(zf.read("poetry_core-1.5.0.dist-info/METADATA"))

    mock_metadata_from_wheel_url = mocker.patch(
        "poetry.repositories.http_repository.metadata_from_wheel_url",
        return_value=metadata,
    )
    mock_download = mocker.patch(
        "poetry.repositories.http_repository.download_file",
        side_effect=lambda _, dest, *args, **kwargs: shutil.copy(filepath, dest),
    )

    domain = "foo.com"
    url = f"https://{domain}/{filename}"
    repo = MockRepository(lazy_wheel)
    assert not repo._supports_range_requests
    if lazy_wheel and supports_range_requests is not None:
        repo._supports_range_requests[domain] = supports_range_requests

    info = repo._get_info_from_wheel(Link(url))
    assert info.name == "poetry-core"
    assert info.version == "1.5.0"
    assert info.requires_dist == [
        'importlib-metadata (>=1.7.0) ; python_version < "3.8"'
    ]

    if lazy_wheel and supports_range_requests is not False:
        mock_metadata_from_wheel_url.assert_called_once_with(
            filename, url, repo.session
        )
        mock_download.assert_not_called()
        assert repo._supports_range_requests[domain] is True
    else:
        mock_metadata_from_wheel_url.assert_not_called()
        mock_download.assert_called_once_with(
            url, mocker.ANY, session=repo.session, raise_accepts_ranges=lazy_wheel
        )
        if lazy_wheel:
            assert repo._supports_range_requests[domain] is False
        else:
            assert domain not in repo._supports_range_requests


def test_get_info_from_wheel_state_sequence(mocker: MockerFixture) -> None:
    """
    1. We know nothing:
       Try range requests, which are not supported and fall back to complete download.
    2. Range requests were not supported so far:
       We do not try range requests again.
    3. Range requests were still not supported so far:
       We do not try range requests again, but we notice that the response header
       contains "Accept-Ranges: bytes", so range requests are at least supported
       for some files, which means we want to try again.
    4. Range requests are supported for some files:
       We try range requests (success).
    5. Range requests are supported for some files:
       We try range requests (failure), but do not forget that range requests are
       supported for some files.
    6. Range requests are supported for some files:
       We try range requests (success).
    """
    mock_metadata_from_wheel_url = mocker.patch(
        "poetry.repositories.http_repository.metadata_from_wheel_url"
    )
    mock_download = mocker.patch("poetry.repositories.http_repository.download_file")

    filename = "poetry_core-1.5.0-py3-none-any.whl"
    domain = "foo.com"
    link = Link(f"https://{domain}/{filename}")
    repo = MockRepository()

    # 1. range request and download
    mock_metadata_from_wheel_url.side_effect = HTTPRangeRequestUnsupported
    repo._get_info_from_wheel(link)
    assert mock_metadata_from_wheel_url.call_count == 1
    assert mock_download.call_count == 1
    assert mock_download.call_args[1]["raise_accepts_ranges"] is False

    # 2. only download
    repo._get_info_from_wheel(link)
    assert mock_metadata_from_wheel_url.call_count == 1
    assert mock_download.call_count == 2
    assert mock_download.call_args[1]["raise_accepts_ranges"] is True

    # 3. download and range request
    mock_metadata_from_wheel_url.side_effect = None
    mock_download.side_effect = HTTPRangeRequestSupported
    repo._get_info_from_wheel(link)
    assert mock_metadata_from_wheel_url.call_count == 2
    assert mock_download.call_count == 3
    assert mock_download.call_args[1]["raise_accepts_ranges"] is True

    # 4. only range request
    repo._get_info_from_wheel(link)
    assert mock_metadata_from_wheel_url.call_count == 3
    assert mock_download.call_count == 3

    # 5. range request and download
    mock_metadata_from_wheel_url.side_effect = HTTPRangeRequestUnsupported
    mock_download.side_effect = None
    repo._get_info_from_wheel(link)
    assert mock_metadata_from_wheel_url.call_count == 4
    assert mock_download.call_count == 4
    assert mock_download.call_args[1]["raise_accepts_ranges"] is False

    # 6. only range request
    mock_metadata_from_wheel_url.side_effect = None
    repo._get_info_from_wheel(link)
    assert mock_metadata_from_wheel_url.call_count == 5
    assert mock_download.call_count == 4
