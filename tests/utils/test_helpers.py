from __future__ import annotations

import contextlib
import sys
import tarfile

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.utils._compat import WINDOWS
from poetry.utils.download import Downloader
from poetry.utils.download import HTTPRangeRequestSupportedError
from poetry.utils.download import download_file
from poetry.utils.helpers import directory
from poetry.utils.helpers import ensure_path
from poetry.utils.helpers import extractall
from poetry.utils.helpers import get_file_hash
from poetry.utils.helpers import get_highest_priority_hash_type
from poetry.utils.helpers import merge_dicts


if TYPE_CHECKING:
    from tests.types import FixtureDirGetter


@pytest.mark.parametrize("raises", [False, True], ids=["normal-exit", "exception"])
def test_directory_restores_working_directory(tmp_path: Path, raises: bool) -> None:
    cwd = Path.cwd()

    with (
        pytest.raises(RuntimeError) if raises else contextlib.nullcontext(),
        directory(tmp_path),
    ):
        assert Path.cwd() == tmp_path
        if raises:
            raise RuntimeError("expected failure")

    assert Path.cwd() == cwd


def test_merge_dicts_merges_nested_mappings() -> None:
    config = {
        "installer": {"parallel": True, "max-workers": 4},
        "virtualenvs": {"create": True},
    }

    merge_dicts(
        config,
        {
            "installer": {"max-workers": 8},
            "repositories": {"foo": {"url": "https://foo.example/simple/"}},
        },
    )

    assert config == {
        "installer": {"parallel": True, "max-workers": 8},
        "virtualenvs": {"create": True},
        "repositories": {"foo": {"url": "https://foo.example/simple/"}},
    }


def test_default_hash(fixture_dir: FixtureDirGetter) -> None:
    sha_256 = "9fa123ad707a5c6c944743bf3e11a0e80d86cb518d3cf25320866ca3ef43e2ad"
    assert get_file_hash(fixture_dir("distributions") / "demo-0.1.0.tar.gz") == sha_256


@pytest.mark.parametrize(
    "hash_name,expected",
    [
        ("sha224", "d26bd24163fe91c16b4b0162e773514beab77b76114d9faf6a31e350"),
        (
            "sha3_512",
            "196f4af9099185054ed72ca1d4c57707da5d724df0af7c3dfcc0fd018b0e0533908e790a291600c7d196fe4411b4f5f6db45213fe6e5cd5512bf18b2e9eff728",
        ),
        (
            "blake2s",
            "6dd9007d36c106defcf362cc637abeca41e8e93999928c8fcfaba515ed33bc93",
        ),
        (
            "sha3_384",
            "787264d7885a0c305d2ee4daecfff435d11818399ef96cacef7e7c6bb638ce475f630d39fdd2800ca187dcd0071dc410",
        ),
        (
            "blake2b",
            "077a34e8252c8f6776bddd0d34f321cc52762cb4c11a1c7aa9b6168023f1722caf53c9f029074a6eb990a8de341d415dd986293bc2a2fccddad428be5605696e",
        ),
        (
            "sha256",
            "9fa123ad707a5c6c944743bf3e11a0e80d86cb518d3cf25320866ca3ef43e2ad",
        ),
        (
            "sha512",
            "766ecf369b6bdf801f6f7bbfe23923cc9793d633a55619472cd3d5763f9154711fbf57c8b6ca74e4a82fa9bd8380af831e7b8668e68e362669fc60b1d81d79ad",
        ),
        (
            "sha384",
            "c638f32460f318035e4600284ba64fb531630740aebd33885946e527002d742787ff09eb65fd81bc34ce5ff5ef11cfe8",
        ),
        ("sha3_224", "72980fc7bdf8c4d34268dc469442b09e1ccd2a8ff390954fc4d55a5a"),
        ("sha1", "91b585bd38f72d7ceedb07d03f94911b772fdc4c"),
        (
            "sha3_256",
            "7da5c08b416e6bcb339d6bedc0fe077c6e69af00607251ef4424c356ea061fcb",
        ),
    ],
)
def test_guaranteed_hash(
    hash_name: str, expected: str, fixture_dir: FixtureDirGetter
) -> None:
    file_path = fixture_dir("distributions") / "demo-0.1.0.tar.gz"
    assert get_file_hash(file_path, hash_name) == expected


@pytest.mark.parametrize(
    "hash_types,expected",
    [
        (("sha512", "sha3_512", "md5"), "sha3_512"),
        ("md5", "md5"),
        (("blah", "blah_blah"), None),
        ((), None),
    ],
)
def test_highest_priority_hash_type(hash_types: set[str], expected: str | None) -> None:
    assert get_highest_priority_hash_type(hash_types, "Blah") == expected


def test_ensure_path_converts_string(tmp_path: Path) -> None:
    assert tmp_path.exists()
    assert ensure_path(path=tmp_path.as_posix(), is_directory=True) == tmp_path


def test_ensure_path_does_not_convert_path(tmp_path: Path) -> None:
    assert tmp_path.exists()
    assert Path(tmp_path.as_posix()) is not tmp_path

    result = ensure_path(path=tmp_path, is_directory=True)

    assert result == tmp_path
    assert result is tmp_path


def test_ensure_path_is_directory_parameter(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        ensure_path(path=tmp_path, is_directory=False)

    assert ensure_path(path=tmp_path, is_directory=True) is tmp_path


@pytest.mark.parametrize(
    ("is_directory", "name"),
    [(False, "some_file.txt"), (True, "some_directory")],
    ids=["file", "directory"],
)
def test_ensure_path_existing_type(
    tmp_path: Path, is_directory: bool, name: str
) -> None:
    path = tmp_path / name
    assert not path.exists()

    with pytest.raises(ValueError):
        ensure_path(path=path, is_directory=is_directory)

    if is_directory:
        path.mkdir()
    else:
        path.write_text("foobar", encoding="utf-8")

    assert ensure_path(path=path, is_directory=is_directory) is path


@pytest.mark.parametrize("relative", [False, True])
@pytest.mark.parametrize("existing", [False, True])
def test_extractall_sdist_no_path_traversal(
    tmp_path: Path, relative: bool, existing: bool
) -> None:
    import io
    import tarfile

    archive = tmp_path / "traversal.tar.gz"
    dest = tmp_path / "dest"
    dest.mkdir()

    target = tmp_path / "traversal.txt"
    if existing:
        target.write_text("original", encoding="utf-8")

    with tarfile.open(archive, "w:gz") as tar:
        b = b"path traversal"
        t = tarfile.TarInfo("../traversal.txt" if relative else target.as_posix())
        t.size = len(b)
        tar.addfile(t, io.BytesIO(b))

    has_data_filter = hasattr(tarfile, "data_filter")
    # The stdlib implementation just strips the leading "/" from absolute paths
    # and extracts them relative to the target directory (except for Windows).
    # We do not care and raise an error.
    raises = (
        relative
        or WINDOWS
        or not has_data_filter
        or sys.version_info[:3] in {(3, 10, 12), (3, 11, 4)}
    )
    exceptions: tuple[type[Exception], ...]
    if has_data_filter:
        if relative:
            exceptions = (tarfile.OutsideDestinationError, ValueError)
        else:
            exceptions = (tarfile.AbsolutePathError, ValueError)
    else:
        # tarfile.OutsideDestinationError does not exist
        exceptions = (ValueError,)

    with pytest.raises(exceptions) if raises else contextlib.nullcontext():
        extractall(source=archive, dest=dest, zip=False)

    if existing:
        assert target.exists()
        assert target.read_text(encoding="utf-8") == "original"
    else:
        assert not target.exists()
    if not raises:
        # check that expected location exists, otherwise we have to check
        # that there is no traversal in an unexpected location
        assert (dest / target.as_posix().lstrip("/")).exists()


@pytest.mark.parametrize("link_type", [tarfile.SYMTYPE, tarfile.LNKTYPE])
@pytest.mark.parametrize("relative", [False, True])
@pytest.mark.parametrize("existing", [False, True])
def test_extractall_sdist_no_symlink_path_traversal(
    tmp_path: Path, link_type: bytes, relative: bool, existing: bool
) -> None:
    import io
    import tarfile

    archive = tmp_path / "traversal.tar.gz"
    dest = tmp_path / "dest"
    dest.mkdir()

    target = tmp_path / "traversal.txt"
    if existing:
        target.write_text("original", encoding="utf-8")

    with tarfile.open(archive, "w:gz") as tar:
        # We use a link in a subdirectory to test the difference
        # between symlinks and hardlinks:
        # symlinks are relative to the directory of the symlink,
        # while hardlinks are relative to the root of the archive
        s = tarfile.TarInfo("sub/link")
        s.type = link_type
        if relative:
            s.linkname = (
                "../../traversal.txt"
                if link_type == tarfile.SYMTYPE
                else "../traversal.txt"
            )
        else:
            s.linkname = target.as_posix()
        tar.addfile(s)
        p = b"path traversal"
        f = tarfile.TarInfo("sub/link")
        f.size = len(p)
        tar.addfile(f, io.BytesIO(p))

    exceptions: tuple[type[Exception], ...]
    if hasattr(tarfile, "data_filter"):
        exceptions = (
            tarfile.AbsoluteLinkError,
            tarfile.LinkOutsideDestinationError,
            ValueError,
        )
    else:
        # tarfile.OutsideDestinationError does not exist
        exceptions = (ValueError,)

    with pytest.raises(exceptions):
        extractall(source=archive, dest=dest, zip=False)

    if existing:
        assert target.exists()
        assert target.read_text(encoding="utf-8") == "original"
    else:
        assert not target.exists()


@pytest.mark.parametrize("existing", [False, True])
def test_extractall_wheel_no_path_traversal(
    tmp_path: Path, wheel_with_path_traversal: Path, existing: bool
) -> None:
    """see also test_no_path_traversal in test_wheel_installer.py"""
    dest = tmp_path / "dest" / "dir"
    dest.mkdir(parents=True)
    target = tmp_path / "traversal.txt"
    if existing:
        target.write_text("original", encoding="utf-8")

    extractall(source=wheel_with_path_traversal, dest=dest, zip=True)

    if existing:
        assert target.exists()
        assert target.read_text(encoding="utf-8") == "original"
    else:
        assert not target.exists()

    # target is "../.." but also check ".." just to be sure
    assert not (dest.parent / "traversal.txt").exists()


@pytest.mark.parametrize("existing", [False, True])
def test_extractall_wheel_no_path_traversal_via_symlink(
    tmp_path: Path, wheel_with_path_traversal_via_symlink: Path, existing: bool
) -> None:
    """see also test_no_path_traversal_via_symlink in test_wheel_installer.py"""
    dest = tmp_path / "dest" / "dir"
    dest.mkdir(parents=True)
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    target = target_dir / "traversal.txt"
    if existing:
        target.write_text("original", encoding="utf-8")

    with pytest.raises(FileNotFoundError if WINDOWS else NotADirectoryError):
        extractall(source=wheel_with_path_traversal_via_symlink, dest=dest, zip=True)

    assert target_dir.exists()
    if existing:
        assert target.exists()
        assert target.read_text(encoding="utf-8") == "original"
    else:
        assert not target.exists()


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Downloader", Downloader),
        ("download_file", download_file),
        ("HTTPRangeRequestSupportedError", HTTPRangeRequestSupportedError),
    ],
)
def test_deprecated_helpers_download_reexports(name: str, expected: object) -> None:
    from poetry.utils import helpers

    with pytest.warns(DeprecationWarning, match=r"poetry\.utils\.download"):
        assert getattr(helpers, name) is expected


def test_unknown_helpers_attribute_still_raises_attribute_error() -> None:
    from poetry.utils import helpers

    with pytest.raises(AttributeError):
        helpers.definitely_not_a_real_attribute  # noqa: B018
