from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from poetry.core.packages.utils.link import Link

from poetry.packages.direct_origin import DirectOrigin
from poetry.utils.cache import ArtifactCache


if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from tests.types import FixtureDirGetter


def test_direct_origin_get_package_from_file(fixture_dir: FixtureDirGetter) -> None:
    wheel_path = fixture_dir("distributions") / "demo-0.1.2-py2.py3-none-any.whl"
    package = DirectOrigin.get_package_from_file(wheel_path)
    assert package.name == "demo"
    assert package.files == [
        {
            "file": "demo-0.1.2-py2.py3-none-any.whl",
            "hash": "sha256:55dde4e6828081de7a1e429f33180459c333d9da593db62a3d75a8f5e505dde1",
            "size": 1552,
        }
    ]


def test_direct_origin_caches_url_dependency(tmp_path: Path) -> None:
    artifact_cache = ArtifactCache(cache_dir=tmp_path)
    direct_origin = DirectOrigin(artifact_cache)
    url = "https://files.pythonhosted.org/distributions/demo-0.1.0-py2.py3-none-any.whl"

    package = direct_origin.get_package_from_url(url)

    assert package.name == "demo"
    assert package.files == [
        {
            "file": "demo-0.1.0-py2.py3-none-any.whl",
            "hash": "sha256:70e704135718fffbcbf61ed1fc45933cfd86951a744b681000eaaa75da31f17a",
            "size": 1116,
        }
    ]
    assert artifact_cache.get_cached_archive_for_link(Link(url), strict=True)


def test_direct_origin_does_not_download_url_dependency_when_cached(
    fixture_dir: FixtureDirGetter, mocker: MockerFixture
) -> None:
    artifact_cache = MagicMock()
    artifact_cache.get_cached_archive_for_link = MagicMock(
        return_value=fixture_dir("distributions") / "demo-0.1.2-py2.py3-none-any.whl"
    )
    direct_origin = DirectOrigin(artifact_cache)
    url = "https://files.pythonhosted.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
    download_file = mocker.patch(
        "poetry.packages.direct_origin.DirectOrigin._download_file",
        side_effect=Exception("download_file should not be called"),
    )

    package = direct_origin.get_package_from_url(url)

    assert package.name == "demo"
    assert package.files == [
        {
            "file": "demo-0.1.2-py2.py3-none-any.whl",
            "hash": "sha256:55dde4e6828081de7a1e429f33180459c333d9da593db62a3d75a8f5e505dde1",
            "size": 1552,
        }
    ]
    artifact_cache.get_cached_archive_for_link.assert_called_once_with(
        Link(url), strict=True, download_func=download_file
    )
