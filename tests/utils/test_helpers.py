from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.core.utils.helpers import parse_requires

from poetry.utils.helpers import get_file_hash


if TYPE_CHECKING:
    from tests.types import FixtureDirGetter


def test_parse_requires():
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
"""  # noqa: E501
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
        'typing>=3.6.0.0,<4.0.0.0 ; (python_version >= "2.7.0.0" and python_version < "2.8.0.0") or (python_version >= "3.4.0.0" and python_version < "3.5.0.0")',  # noqa: E501
        'virtualenv>=15.2.0.0,<16.0.0.0 ; python_version >= "2.7.0.0" and python_version < "2.8.0.0"',  # noqa: E501
        'pathlib2>=2.3.0.0,<3.0.0.0 ; python_version >= "2.7.0.0" and python_version < "2.8.0.0"',  # noqa: E501
        'zipfile36>=0.1.0.0,<0.2.0.0 ; python_version >= "3.4.0.0" and python_version < "3.6.0.0"',  # noqa: E501
        'isort@ git+git://github.com/timothycrosley/isort.git@e63ae06ec7d70b06df9e528357650281a3d3ec22#egg=isort ; extra == "dev"',  # noqa: E501
    ]
    # fmt: on
    assert result == expected


def test_default_hash(fixture_dir: FixtureDirGetter) -> None:
    root_dir = Path(__file__).parent.parent.parent
    file_path = root_dir / fixture_dir("distributions/demo-0.1.0.tar.gz")
    sha_256 = "72e8531e49038c5f9c4a837b088bfcb8011f4a9f76335c8f0654df6ac539b3d6"
    assert get_file_hash(file_path) == sha_256


try:
    from hashlib import algorithms_guaranteed
except ImportError:
    algorithms_guaranteed = {"md5", "sha1", "sha224", "sha256", "sha384", "sha512"}


@pytest.mark.parametrize(
    "hash_name,expected",
    [
        (hash_name, value)
        for hash_name, value in [
            ("sha224", "972d02f36539a98599aed0566bc8aaf3e6701f4e895dd797d8f5248e"),
            (
                "sha3_512",
                "c04ee109ae52d6440445e24dbd6d244a1d0f0289ef79cb7ba9bc3c139c0237169af9a8f61cd1cf4fc17f853ddf84f97c475ac5bb6c91a4aff0b825b884d4896c",  # noqa: E501
            ),
            (
                "blake2s",
                "c336ecbc9d867c9d860accfba4c3723c51c4b5c47a1e0a955e1c8df499e36741",
            ),
            (
                "sha3_384",
                "d4abb2459941369aabf8880c5287b7eeb80678e14f13c71b9ecf64c772029dc3f93939590bea9ecdb51a1d1a74fefc5a",  # noqa: E501
            ),
            (
                "blake2b",
                "48e70abac547ab38e2330e6e6743a0c0f6274dcaa6df2c98135a78a9dd5b04a072d551fc3851b34da03eb0bf50dd71c7f32a8c36956e99fd6c66491bc7844800",  # noqa: E501
            ),
            (
                "sha256",
                "72e8531e49038c5f9c4a837b088bfcb8011f4a9f76335c8f0654df6ac539b3d6",
            ),
            (
                "sha512",
                "e08a00a4b86358e49a318e7e3ba7a3d2fabdd17a2fef95559a0af681ea07ab1296b0b8e11e645297da296290661dc07ae3c8f74eab66bd18a80dce0c0ccb355b",  # noqa: E501
            ),
            (
                "sha384",
                "aa3144e28c6700a83247e8ec8711af5d3f5f75997990d48ec41e66bd275b3d0e19ee6f2fe525a358f874aa717afd06a9",  # noqa: E501
            ),
            ("sha3_224", "64bfc6e4125b4c6d67fd88ad1c7d1b5c4dc11a1970e433cd576c91d4"),
            ("sha1", "4c057579005ac3e68e951a11ffdc4b27c6ae16af"),
            (
                "sha3_256",
                "ba3d2a964b0680b6dc9565a03952e29c294c785d5a2307d3e2d785d73b75ed7e",
            ),
        ]
        if hash_name in algorithms_guaranteed
    ],
)
def test_guaranteed_hash(
    hash_name: str, expected: str, fixture_dir: FixtureDirGetter
) -> None:
    root_dir = Path(__file__).parent.parent.parent
    file_path = root_dir / fixture_dir("distributions/demo-0.1.0.tar.gz")
    assert get_file_hash(file_path, hash_name) == expected
