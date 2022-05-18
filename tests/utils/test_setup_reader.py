from __future__ import annotations

import os

from typing import TYPE_CHECKING

import pytest

from poetry.core.version.exceptions import InvalidVersion

from poetry.utils.setup_reader import SetupReader


if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture()
def setup() -> Callable[[str], str]:
    def _setup(name: str) -> str:
        return os.path.join(os.path.dirname(__file__), "fixtures", "setups", name)

    return _setup


def test_setup_reader_read_first_level_setup_call_with_direct_types(
    setup: Callable[[str], str]
):
    result = SetupReader.read_from_directory(setup("flask"))

    expected_name = "Flask"
    expected_version = None
    expected_install_requires = [
        "Werkzeug>=0.14",
        "Jinja2>=2.10",
        "itsdangerous>=0.24",
        "click>=5.1",
    ]
    expected_extras_require = {
        "dotenv": ["python-dotenv"],
        "dev": [
            "pytest>=3",
            "coverage",
            "tox",
            "sphinx",
            "pallets-sphinx-themes",
            "sphinxcontrib-log-cabinet",
        ],
        "docs": ["sphinx", "pallets-sphinx-themes", "sphinxcontrib-log-cabinet"],
    }
    expected_python_requires = ">=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*"

    assert result["name"] == expected_name
    assert result["version"] == expected_version
    assert result["install_requires"] == expected_install_requires
    assert result["extras_require"] == expected_extras_require
    assert result["python_requires"] == expected_python_requires


def test_setup_reader_read_first_level_setup_call_with_variables(
    setup: Callable[[str], str]
):
    result = SetupReader.read_from_directory(setup("requests"))

    expected_name = None
    expected_version = None
    expected_install_requires = [
        "chardet>=3.0.2,<3.1.0",
        "idna>=2.5,<2.8",
        "urllib3>=1.21.1,<1.25",
        "certifi>=2017.4.17",
    ]
    expected_extras_require = {
        "security": ["pyOpenSSL >= 0.14", "cryptography>=1.3.4", "idna>=2.0.0"],
        "socks": ["PySocks>=1.5.6, !=1.5.7"],
        'socks:sys_platform == "win32" and python_version == "2.7"': ["win_inet_pton"],
    }
    expected_python_requires = ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*"

    assert result["name"] == expected_name
    assert result["version"] == expected_version
    assert result["install_requires"] == expected_install_requires
    assert result["extras_require"] == expected_extras_require
    assert result["python_requires"] == expected_python_requires


def test_setup_reader_read_sub_level_setup_call_with_direct_types(
    setup: Callable[[str], str]
):
    result = SetupReader.read_from_directory(setup("sqlalchemy"))

    expected_name = "SQLAlchemy"
    expected_version = None
    expected_install_requires = []
    expected_extras_require = {
        "mysql": ["mysqlclient"],
        "pymysql": ["pymysql"],
        "postgresql": ["psycopg2"],
        "postgresql_pg8000": ["pg8000"],
        "postgresql_psycopg2cffi": ["psycopg2cffi"],
        "oracle": ["cx_oracle"],
        "mssql_pyodbc": ["pyodbc"],
        "mssql_pymssql": ["pymssql"],
    }

    assert result["name"] == expected_name
    assert result["version"] == expected_version
    assert result["install_requires"] == expected_install_requires
    assert result["extras_require"] == expected_extras_require
    assert result["python_requires"] is None


def test_setup_reader_read_setup_cfg(setup: Callable[[str], str]):
    result = SetupReader.read_from_directory(setup("with-setup-cfg"))

    expected_name = "with-setup-cfg"
    expected_version = "1.2.3"
    expected_install_requires = ["six", "tomlkit"]
    expected_extras_require = {
        "validation": ["cerberus"],
        "tests": ["pytest", "pytest-xdist", "pytest-cov"],
    }
    expected_python_requires = ">=2.6,!=3.0,!=3.1,!=3.2,!=3.3"

    assert result["name"] == expected_name
    assert result["version"] == expected_version
    assert result["install_requires"] == expected_install_requires
    assert result["extras_require"] == expected_extras_require
    assert result["python_requires"] == expected_python_requires


def test_setup_reader_read_setup_cfg_with_attr(setup: Callable[[str], str]):
    with pytest.raises(InvalidVersion):
        SetupReader.read_from_directory(setup("with-setup-cfg-attr"))


def test_setup_reader_read_setup_kwargs(setup: Callable[[str], str]):
    result = SetupReader.read_from_directory(setup("pendulum"))

    expected_name = "pendulum"
    expected_version = "2.0.4"
    expected_install_requires = ["python-dateutil>=2.6,<3.0", "pytzdata>=2018.3"]
    expected_extras_require = {':python_version < "3.5"': ["typing>=3.6,<4.0"]}
    expected_python_requires = ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*"

    assert result["name"] == expected_name
    assert result["version"] == expected_version
    assert result["install_requires"] == expected_install_requires
    assert result["extras_require"] == expected_extras_require
    assert result["python_requires"] == expected_python_requires


def test_setup_reader_read_setup_call_in_main(setup: Callable[[str], str]):
    result = SetupReader.read_from_directory(setup("pyyaml"))

    expected_name = "PyYAML"
    expected_version = "3.13"
    expected_install_requires = []
    expected_extras_require = {}
    expected_python_requires = None

    assert result["name"] == expected_name
    assert result["version"] == expected_version
    assert result["install_requires"] == expected_install_requires
    assert result["extras_require"] == expected_extras_require
    assert result["python_requires"] == expected_python_requires


def test_setup_reader_read_extras_require_with_variables(setup: Callable[[str], str]):
    result = SetupReader.read_from_directory(setup("extras_require_with_vars"))

    expected_name = "extras_require_with_vars"
    expected_version = "0.0.1"
    expected_install_requires = []
    expected_extras_require = {"test": ["pytest"]}
    expected_python_requires = None

    assert result["name"] == expected_name
    assert result["version"] == expected_version
    assert result["install_requires"] == expected_install_requires
    assert result["extras_require"] == expected_extras_require
    assert result["python_requires"] == expected_python_requires


def test_setup_reader_setuptools(setup: Callable[[str], str]):
    result = SetupReader.read_from_directory(setup("setuptools_setup"))

    expected_name = "my_package"
    expected_version = "0.1.2"

    assert result["name"] == expected_name
    assert result["version"] == expected_version
