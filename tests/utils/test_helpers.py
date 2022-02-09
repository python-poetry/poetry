import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.core.utils.helpers import parse_requires
from src.poetry.utils.helpers import robust_rmtree

from poetry.utils.helpers import canonicalize_name
from poetry.utils.helpers import get_cert
from poetry.utils.helpers import get_client_cert


if TYPE_CHECKING:
    from tests.conftest import Config


def test_robust_rmtree(mocker):
    mocked_rmtree = mocker.patch('shutil.rmtree')

    # this should work after an initial exception
    name = tempfile.mkdtemp()
    mocked_rmtree.side_effect = [OSError("Couldn't delete file yet, waiting for references to clear", "mocked path"), None]
    robust_rmtree(name)

    # this should give up after retrying multiple times
    name = tempfile.mkdtemp()
    mocked_rmtree.side_effect = OSError("Couldn't delete file yet, this error won't go away after first attempt")
    with pytest.raises(OSError):
        robust_rmtree(name, max_timeout=0.04)

    # clear the side effect (breaks the tear-down otherwise)
    mocked_rmtree.side_effect = None


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


def test_get_cert(config: "Config"):
    ca_cert = "path/to/ca.pem"
    config.merge({"certificates": {"foo": {"cert": ca_cert}}})

    assert get_cert(config, "foo") == Path(ca_cert)


def test_get_client_cert(config: "Config"):
    client_cert = "path/to/client.pem"
    config.merge({"certificates": {"foo": {"client-cert": client_cert}}})

    assert get_client_cert(config, "foo") == Path(client_cert)


test_canonicalize_name_cases = [
    ("flask", "flask"),
    ("Flask", "flask"),
    ("FLASK", "flask"),
    ("FlAsK", "flask"),
    ("fLaSk57", "flask57"),
    ("flask-57", "flask-57"),
]


@pytest.mark.parametrize("test, expected", test_canonicalize_name_cases)
def test_canonicalize_name(test: str, expected: str):
    canonicalized_name = canonicalize_name(test)
    assert canonicalized_name == expected
