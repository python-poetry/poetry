from __future__ import annotations

import base64
import re

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest

from poetry.core.utils.helpers import parse_requires
from requests.exceptions import ChunkedEncodingError

from poetry.utils.helpers import Downloader
from poetry.utils.helpers import HTTPRangeRequestSupportedError
from poetry.utils.helpers import download_file
from poetry.utils.helpers import ensure_path
from poetry.utils.helpers import get_file_hash
from poetry.utils.helpers import get_highest_priority_hash_type
from poetry.utils.helpers import pluralize


if TYPE_CHECKING:
    from httpretty import httpretty
    from httpretty.core import HTTPrettyRequest

    from tests.conftest import Config
    from tests.types import FixtureDirGetter


def test_pluralize() -> None:
    assert pluralize(1, "apple") == "apple"
    assert pluralize(0, "apple") == "apples"
    assert pluralize(2, "apple") == "apples"
    assert pluralize(3, "") == "s"



def test_parse_requires() -> None:
    requires = """\
jsonschema>=2.6.0.0,<3.0.0.0
lockfile>=0.12.0.0,<0.13.0.0
pip-tools>=1.11.0.0,<2.0.0.0
pkginfo>=1.4.0.0,<2.0.0.0
pyrsistent>=0.14.2.0,<0.15.0.0
toml>=0.9.0.0,<0.10.0.0
cleo>=0.6.0.0,<0.7.0.0
cachy>=0.1.1.0,<0.2.0.0
cachecontrol>=0.12.4.0,<0.13.0.0
requests>=2.18.0.0,<3.0.0.0
msgpack-python>=0.5.0.0,<0.6.0.0
pyparsing>=2.2.0.0,<3.0.0.0
requests-toolbelt>=0.8.0.0,<0.9.0.0

[:(python_version >= "2.7.0.0" and python_version < "2.8.0.0")\
 or (python_version >= "3.4.0.0" and python_version < "3.5.0.0")]
typing>=3.6.0.0,<4.0.0.0

[:python_version >= "2.7.0.0" and python_version < "2.8.0.0"]
virtualenv>=15.2.0.0,<16.0.0.0
pathlib2>=2.3.0.0,<3.0.0.0

[:python_version >= "3.4.0.0" and python_version < "3.6.0.0"]
zipfile36>=0.1.0.0,<0.2.0.0

[dev]
isort@ git+git://github.com/timothycrosley/isort.git@e63ae06ec7d70b06df9e528357650281a3d3ec22#egg=isort
"""
    result = parse_requires(requires)
    # fmt: off
    expected = [
        "jsonschema>=2.6.0.0,<3.0.0.0",
        "lockfile>=0.12.0.0,<0.13.0.0",
        "pip-tools>=1.11.0.0,<2.0.0.0",
        "pkginfo>=1.4.0.0,<2.0.0.0",
        "pyrsistent>=0.14.2.0,<0.15.0.0",
        "toml>=0.9.0.0,<0.10.0.0",
        "cleo>=0.6.0.0,<0.7.0.0",
        "cachy>=0.1.1.0,<0.2.0.0",
        "cachecontrol>=0.12.4.0,<0.13.0.0",
        "requests>=2.18.0.0,<3.0.0.0",
        "msgpack-python>=0.5.0.0,<0.6.0.0",
        "pyparsing>=2.2.0.0,<3.0.0.0",
        "requests-toolbelt>=0.8.0.0,<0.9.0.0",
        'typing>=3.6.0.0,<4.0.0.0 ; (python_version >= "2.7.0.0" and python_version < "2.8.0.0") or (python_version >= "3.4.0.0" and python_version < "3.5.0.0")',
        'virtualenv>=15.2.0.0,<16.0.0.0 ; python_version >= "2.7.0.0" and python_version < "2.8.0.0"',
        'pathlib2>=2.3.0.0,<3.0.0.0 ; python_version >= "2.7.0.0" and python_version < "2.8.0.0"',
        'zipfile36>=0.1.0.0,<0.2.0.0 ; python_version >= "3.4.0.0" and python_version < "3.6.0.0"',
        'isort@ git+git://github.com/timothycrosley/isort.git@e63ae06ec7d70b06df9e528357650281a3d3ec22#egg=isort ; extra == "dev"',
    ]
    # fmt: on
    assert result == expected


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


def test_download_file(
    http: type[httpretty], fixture_dir: FixtureDirGetter, tmp_path: Path
) -> None:
    file_path = fixture_dir("distributions") / "demo-0.1.0.tar.gz"
    url = "https://foo.com/demo-0.1.0.tar.gz"
    http.register_uri(http.GET, url, body=file_path.read_bytes())
    dest = tmp_path / "demo-0.1.0.tar.gz"

    download_file(url, dest)

    expect_sha_256 = "9fa123ad707a5c6c944743bf3e11a0e80d86cb518d3cf25320866ca3ef43e2ad"
    assert get_file_hash(dest) == expect_sha_256
    assert http.last_request().headers["Accept-Encoding"] == "Identity"


def test_download_file_recover_from_error(
    http: type[httpretty], fixture_dir: FixtureDirGetter, tmp_path: Path
) -> None:
    file_path = fixture_dir("distributions") / "demo-0.1.0.tar.gz"
    file_body = file_path.read_bytes()
    file_length = len(file_body)
    url = "https://foo.com/demo-0.1.0.tar.gz"

    def handle_request(
        request: HTTPrettyRequest, uri: str, response_headers: dict[str, Any]
    ) -> tuple[int, dict[str, Any], bytes]:
        if request.headers.get("Range") is None:
            response_headers["Content-Length"] = str(file_length)
            response_headers["Accept-Ranges"] = "bytes"
            return 200, response_headers, file_body[: file_length // 2]
        else:
            start = int(
                request.headers.get("Range", "bytes=0-").split("=")[1].split("-")[0]
            )
            return 206, response_headers, file_body[start:]

    http.register_uri(http.GET, url, body=handle_request)
    dest = tmp_path / "demo-0.1.0.tar.gz"

    download_file(url, dest, chunk_size=file_length // 2, max_retries=1)

    expect_sha_256 = "9fa123ad707a5c6c944743bf3e11a0e80d86cb518d3cf25320866ca3ef43e2ad"
    assert get_file_hash(dest) == expect_sha_256
    assert http.last_request().headers["Accept-Encoding"] == "Identity"
    assert http.last_request().headers["Range"] == f"bytes={file_length // 2}-"


def test_download_file_fail_when_no_range(
    http: type[httpretty], fixture_dir: FixtureDirGetter, tmp_path: Path
) -> None:
    file_path = fixture_dir("distributions") / "demo-0.1.0.tar.gz"
    file_body = file_path.read_bytes()
    file_length = len(file_body)
    url = "https://foo.com/demo-0.1.0.tar.gz"

    def handle_request(
        request: HTTPrettyRequest, uri: str, response_headers: dict[str, Any]
    ) -> tuple[int, dict[str, Any], bytes]:
        response_headers["Content-Length"] = str(file_length)
        return 200, response_headers, file_body[: file_length // 2]

    http.register_uri(http.GET, url, body=handle_request)
    dest = tmp_path / "demo-0.1.0.tar.gz"
    with pytest.raises(ChunkedEncodingError):
        download_file(url, dest, chunk_size=file_length // 2, max_retries=1)


def test_download_file_fail_when_first_chunk_failed(
    http: type[httpretty], fixture_dir: FixtureDirGetter, tmp_path: Path
) -> None:
    file_path = fixture_dir("distributions") / "demo-0.1.0.tar.gz"
    file_body = file_path.read_bytes()
    file_length = len(file_body)
    url = "https://foo.com/demo-0.1.0.tar.gz"

    def handle_request(
        request: HTTPrettyRequest, uri: str, response_headers: dict[str, Any]
    ) -> tuple[int, dict[str, Any], bytes]:
        response_headers["Content-Length"] = str(file_length)
        response_headers["Accept-Ranges"] = "bytes"
        return 200, response_headers, file_body[: file_length // 2]

    http.register_uri(http.GET, url, body=handle_request)
    dest = tmp_path / "demo-0.1.0.tar.gz"
    with pytest.raises(ChunkedEncodingError):
        download_file(url, dest, chunk_size=file_length, max_retries=1)


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


@pytest.mark.parametrize("accepts_ranges", [False, True])
@pytest.mark.parametrize("raise_accepts_ranges", [False, True])
def test_download_file_raise_accepts_ranges(
    http: type[httpretty],
    fixture_dir: FixtureDirGetter,
    tmp_path: Path,
    accepts_ranges: bool,
    raise_accepts_ranges: bool,
) -> None:
    filename = "demo-0.1.0-py2.py3-none-any.whl"

    def handle_request(
        request: HTTPrettyRequest, uri: str, response_headers: dict[str, Any]
    ) -> tuple[int, dict[str, Any], bytes]:
        file_path = fixture_dir("distributions") / filename
        if accepts_ranges:
            response_headers["Accept-Ranges"] = "bytes"
        return 200, response_headers, file_path.read_bytes()

    url = f"https://foo.com/{filename}"
    http.register_uri(http.GET, url, body=handle_request)
    dest = tmp_path / filename

    if accepts_ranges and raise_accepts_ranges:
        with pytest.raises(HTTPRangeRequestSupportedError):
            download_file(url, dest, raise_accepts_ranges=raise_accepts_ranges)
        assert not dest.exists()
    else:
        download_file(url, dest, raise_accepts_ranges=raise_accepts_ranges)
        assert dest.is_file()


def test_downloader_uses_authenticator_by_default(
    config: Config,
    http: type[httpretty],
    tmp_working_directory: Path,
) -> None:
    import poetry.utils.authenticator

    # force set default authenticator to None so that it is recreated using patched config
    poetry.utils.authenticator._authenticator = None

    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/files/"}},
            "http-basic": {"foo": {"username": "bar", "password": "baz"}},
        }
    )

    http.register_uri(
        http.GET,
        re.compile("^https?://foo.bar/(.+?)$"),
    )

    Downloader(
        "https://foo.bar/files/foo-0.1.0.tar.gz",
        tmp_working_directory / "foo-0.1.0.tar.gz",
    )

    request = http.last_request()
    basic_auth = base64.b64encode(b"bar:baz").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


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


def test_ensure_path_file(tmp_path: Path) -> None:
    path = tmp_path.joinpath("some_file.txt")
    assert not path.exists()

    with pytest.raises(ValueError):
        ensure_path(path=path, is_directory=False)

    path.write_text("foobar", encoding="utf-8")
    assert ensure_path(path=path, is_directory=False) is path


def test_ensure_path_directory(tmp_path: Path) -> None:
    path = tmp_path.joinpath("foobar")
    assert not path.exists()

    with pytest.raises(ValueError):
        ensure_path(path=path, is_directory=True)

    path.mkdir()
    assert ensure_path(path=path, is_directory=True) is path
