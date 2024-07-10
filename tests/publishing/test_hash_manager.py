from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import pytest

from poetry.publishing.hash_manager import HashManager


if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from tests.types import FixtureDirGetter


@pytest.fixture
def distributions_dir(fixture_dir: FixtureDirGetter) -> Path:
    return fixture_dir("distributions")


@pytest.mark.parametrize(
    "file, hashes",
    (
        (
            "demo-0.1.0.tar.gz",
            (
                "d1912c917363a64e127318655f7d1fe7",
                "9fa123ad707a5c6c944743bf3e11a0e80d86cb518d3cf25320866ca3ef43e2ad",
                "cb638093d63df647e70b03e963bedc31e021cb088695e29101b69f525e3d5fef",
            ),
        ),
        (
            "demo-0.1.2-py2.py3-none-any.whl",
            (
                "53b4e10d2bfa81a4206221c4b87843d9",
                "55dde4e6828081de7a1e429f33180459c333d9da593db62a3d75a8f5e505dde1",
                "b35b9aab064e88fffe42309550ebe425907fb42ccb3b1d173b7d6b7509f38eac",
            ),
        ),
    ),
)
def test_file_hashes_returns_proper_hashes_for_file(
    file: str, hashes: tuple[str, ...], distributions_dir: Path
) -> None:
    manager = HashManager()
    manager.hash(distributions_dir / file)
    file_hashes = manager.hexdigest()
    assert file_hashes == hashes


def test_file_hashes_returns_none_for_md5_with_fips(
    mocker: MockerFixture, distributions_dir: Path
) -> None:
    # disable md5
    def fips_md5(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("Disabled by FIPS")

    mocker.patch("hashlib.md5", new=fips_md5)

    manager = HashManager()
    manager.hash(distributions_dir / "demo-0.1.0.tar.gz")
    file_hashes = manager.hexdigest()

    assert file_hashes.md5 is None


def test_file_hashes_returns_none_for_blake2_with_fips(
    mocker: MockerFixture, distributions_dir: Path
) -> None:
    # disable md5
    def fips_blake2b(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("Disabled by FIPS")

    mocker.patch("hashlib.blake2b", new=fips_blake2b)

    manager = HashManager()
    manager.hash(distributions_dir / "demo-0.1.0.tar.gz")
    file_hashes = manager.hexdigest()

    assert file_hashes.blake2_256 is None
