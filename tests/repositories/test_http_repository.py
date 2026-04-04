from __future__ import annotations

import contextlib
import logging
import shutil

from datetime import datetime
from datetime import timedelta
from datetime import timezone
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from zipfile import ZipFile

import pytest

from packaging.metadata import parse_email
from packaging.utils import canonicalize_name
from poetry.core.constraints.version import Version
from poetry.core.packages.utils.link import Link

from poetry.inspection.info import PackageInfoError
from poetry.inspection.lazy_wheel import HTTPRangeRequestUnsupportedError
from poetry.repositories.http_repository import HTTPRepository
from poetry.utils.helpers import HTTPRangeRequestSupportedError


if TYPE_CHECKING:
    from packaging.utils import NormalizedName
    from pytest_mock import MockerFixture

    from poetry.config.config import Config


class MockRepository(HTTPRepository):
    DIST_FIXTURES = Path(__file__).parent / "fixtures" / "pypi.org" / "dists"

    def __init__(self, lazy_wheel: bool = True, config: Config | None = None) -> None:
        super().__init__("foo", "https://foo.com", config=config)
        self._lazy_wheel = lazy_wheel

    def _get_release_info(
        self, name: NormalizedName, version: Version
    ) -> dict[str, Any]:
        raise NotImplementedError


@pytest.mark.parametrize("min_release_age", [None, 0, 30])
def test_min_release_age_and_cutoff_is_set(
    mocker: MockerFixture, config: Config, min_release_age: int | None
) -> None:
    config.merge({"solver": {"min-release-age": min_release_age}})

    mocked_now = datetime(2017, 8, 20, tzinfo=timezone.utc)
    mocker.patch(  # type: ignore[call-overload]
        "poetry.repositories.http_repository.datetime",
        wraps=datetime,
        **{"now.return_value": mocked_now},
    )

    repo = MockRepository(config=config)

    assert repo._min_release_age == min_release_age
    if min_release_age:
        assert repo._min_release_age_cutoff == mocked_now - timedelta(
            days=min_release_age
        )
    else:
        assert repo._min_release_age_cutoff is None


@pytest.mark.parametrize(
    ("links", "expected"),
    [
        (  # no upload time
            [Link("https://foo.com/pkg-1.0.tar.gz")],
            False,
        ),
        (  # before cutoff date
            [
                Link(
                    "https://foo.com/pkg-1.0.tar.gz",
                    upload_time="2017-08-09T00:00:00Z",
                ),
            ],
            False,
        ),
        (  # exact cutoff date
            [
                Link(
                    "https://foo.com/pkg-1.0.tar.gz",
                    upload_time="2017-08-10T00:00:00Z",
                ),
            ],
            False,
        ),
        (  # after cutoff date
            [
                Link(
                    "https://foo.com/pkg-1.0.tar.gz",
                    upload_time="2017-08-11T00:00:00Z",
                ),
            ],
            True,
        ),
        (  # some files without upload time, others old enough
            [
                Link("https://foo.com/pkg-1.0.tar.gz"),
                Link(
                    "https://foo.com/pkg-1.0-py3-none-any.whl",
                    upload_time="2017-06-01T00:00:00Z",
                ),
            ],
            False,
        ),
        (  # some files without upload time, others not old enough
            [
                Link("https://foo.com/pkg-1.0.tar.gz"),
                Link(
                    "https://foo.com/pkg-1.0-py3-none-any.whl",
                    upload_time="2017-08-15T00:00:00Z",
                ),
            ],
            True,
        ),
        (  # some files old enough, some files not
            [
                Link(
                    "https://foo.com/pkg-1.0-py3-none-any.whl",
                    upload_time="2017-07-01T00:00:00Z",
                ),
                Link(
                    "https://foo.com/pkg-1.0-py3-none-any.whl",
                    upload_time="2017-08-15T00:00:00Z",
                ),
            ],
            True,
        ),
    ],
)
def test_is_version_too_recent(links: list[Link], expected: bool) -> None:
    repo = MockRepository()
    repo._min_release_age_cutoff = datetime(2017, 8, 10, tzinfo=timezone.utc)
    assert repo._is_version_too_recent(links) == expected


def test_is_version_too_recent_no_cutoff_set() -> None:
    """When no cutoff is set, always returns False."""
    repo = MockRepository()
    assert repo._min_release_age_cutoff is None
    links = [
        Link(
            "https://foo.com/pkg-1.0.tar.gz",
            upload_time="2099-01-01T00:00:00Z",
        )
    ]
    assert not repo._is_version_too_recent(links)


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
            url,
            mocker.ANY,
            session=repo.session,
            raise_accepts_ranges=lazy_wheel,
            max_retries=0,
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
    mock_metadata_from_wheel_url.side_effect = HTTPRangeRequestUnsupportedError

    with contextlib.suppress(PackageInfoError):
        repo._get_info_from_wheel(link)

    assert mock_metadata_from_wheel_url.call_count == 1
    assert mock_download.call_count == 1
    assert mock_download.call_args[1]["raise_accepts_ranges"] is False

    # 2. only download
    with contextlib.suppress(PackageInfoError):
        repo._get_info_from_wheel(link)

    assert mock_metadata_from_wheel_url.call_count == 1
    assert mock_download.call_count == 2
    assert mock_download.call_args[1]["raise_accepts_ranges"] is True

    # 3. download and range request
    mock_metadata_from_wheel_url.side_effect = None
    mock_download.side_effect = HTTPRangeRequestSupportedError

    with contextlib.suppress(PackageInfoError):
        repo._get_info_from_wheel(link)

    assert mock_metadata_from_wheel_url.call_count == 2
    assert mock_download.call_count == 3
    assert mock_download.call_args[1]["raise_accepts_ranges"] is True

    # 4. only range request
    with contextlib.suppress(PackageInfoError):
        repo._get_info_from_wheel(link)

    assert mock_metadata_from_wheel_url.call_count == 3
    assert mock_download.call_count == 3

    # 5. range request and download
    mock_metadata_from_wheel_url.side_effect = HTTPRangeRequestUnsupportedError
    mock_download.side_effect = None

    with contextlib.suppress(PackageInfoError):
        repo._get_info_from_wheel(link)

    assert mock_metadata_from_wheel_url.call_count == 4
    assert mock_download.call_count == 4
    assert mock_download.call_args[1]["raise_accepts_ranges"] is False

    # 6. only range request
    mock_metadata_from_wheel_url.side_effect = None

    with contextlib.suppress(PackageInfoError):
        repo._get_info_from_wheel(link)

    assert mock_metadata_from_wheel_url.call_count == 5
    assert mock_download.call_count == 4


@pytest.mark.parametrize(
    "mock_hashes",
    [
        None,
        {"sha256": "e216b70f013c47b82a72540d34347632c5bfe59fd54f5fe5d51f6a68b19aaf84"},
        {"md5": "be7589b4902793e66d7d979bd8581591"},
    ],
)
def test_calculate_sha256(
    mocker: MockerFixture, mock_hashes: dict[str, Any] | None
) -> None:
    filename = "poetry_core-1.5.0-py3-none-any.whl"
    filepath = MockRepository.DIST_FIXTURES / filename
    mock_download = mocker.patch(
        "poetry.repositories.http_repository.download_file",
        side_effect=lambda _, dest, *args, **kwargs: shutil.copy(filepath, dest),
    )
    domain = "foo.com"
    link = Link(f"https://{domain}/{filename}", hashes=mock_hashes)
    repo = MockRepository()

    calculated_hash = repo.calculate_sha256(link)

    assert mock_download.call_count == 1
    assert (
        calculated_hash
        == "sha256:e216b70f013c47b82a72540d34347632c5bfe59fd54f5fe5d51f6a68b19aaf84"
    )


def test_calculate_sha256_defaults_to_sha256_on_md5_errors(
    mocker: MockerFixture,
) -> None:
    raised_value_error = False

    def mock_hashlib_md5_error() -> None:
        nonlocal raised_value_error
        raised_value_error = True
        raise ValueError(
            "[digital envelope routines: EVP_DigestInit_ex] disabled for FIPS"
        )

    filename = "poetry_core-1.5.0-py3-none-any.whl"
    filepath = MockRepository.DIST_FIXTURES / filename
    mock_download = mocker.patch(
        "poetry.repositories.http_repository.download_file",
        side_effect=lambda _, dest, *args, **kwargs: shutil.copy(filepath, dest),
    )
    mock_hashlib_md5 = mocker.patch("hashlib.md5", side_effect=mock_hashlib_md5_error)

    domain = "foo.com"
    link = Link(
        f"https://{domain}/{filename}",
        hashes={"md5": "be7589b4902793e66d7d979bd8581591"},
    )
    repo = MockRepository()

    calculated_hash = repo.calculate_sha256(link)

    assert raised_value_error
    assert mock_download.call_count == 1
    assert mock_hashlib_md5.call_count == 1
    assert (
        calculated_hash
        == "sha256:e216b70f013c47b82a72540d34347632c5bfe59fd54f5fe5d51f6a68b19aaf84"
    )


@pytest.mark.parametrize(
    ("level", "log_level"), [("info", logging.INFO), ("warning", logging.WARNING)]
)
@pytest.mark.parametrize("reset", [True, False])
def test_log_age_filtered_versions(
    caplog: pytest.LogCaptureFixture, level: str, log_level: int, reset: bool
) -> None:
    repo = MockRepository()
    repo._min_release_age = 7
    repo._age_filtered_versions |= {
        canonicalize_name("B"): {
            Version.parse("2.0"),
            Version.parse("1.5"),
        },
        canonicalize_name("A"): {
            Version.parse("1.0"),
        },
    }

    with caplog.at_level(log_level):
        repo.log_age_filtered_versions(level=level, reset=reset)

    assert len(caplog.records) == 3
    assert "solver.min-release-age=7" in caplog.records[0].message
    # packages are sorted by name
    assert "a: 1.0" in caplog.records[1].message
    assert "b: 1.5, 2.0" in caplog.records[2].message
    assert all(r.levelno == log_level for r in caplog.records)
    if reset:
        assert repo._age_filtered_versions == {}
    else:
        assert repo._age_filtered_versions != {}


def test_log_age_filtered_versions_empty(caplog: pytest.LogCaptureFixture) -> None:
    repo = MockRepository()
    repo._min_release_age = 7
    repo._age_filtered_versions.clear()

    with caplog.at_level(logging.WARNING):
        repo.log_age_filtered_versions(level="warning", reset=False)

    assert len(caplog.records) == 0
