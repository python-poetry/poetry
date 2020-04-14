import os

import pytest

from poetry.utils.setup_reader import SetupReader


@pytest.fixture()
def setup():
    def _setup(name):
        return os.path.join(os.path.dirname(__file__), "fixtures", "setups", name)

    return _setup


def test_setup_reader_read_first_level_setup_call_with_direct_types(setup):
    result = SetupReader.read_from_pep517_hook(setup("flask"))

    expected_name = "Flask"
    expected_version = "1.2.3"
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

    assert expected_name == result["name"]
    assert expected_version == result["version"]
    assert expected_install_requires == result["install_requires"]
    assert expected_extras_require == result["extras_require"]
    assert expected_python_requires == result["python_requires"]


def test_setup_reader_read_first_level_setup_call_with_variables(setup):
    result = SetupReader.read_from_pep517_hook(setup("requests"))

    expected_name = "request"
    expected_version = "1.2.3"
    expected_install_requires = [
        "chardet<3.1.0,>=3.0.2",
        "idna<2.8,>=2.5",
        "urllib3<1.25,>=1.21.1",
        "certifi>=2017.4.17",
    ]
    expected_extras_require = {
        "security": ["pyOpenSSL>=0.14", "cryptography>=1.3.4", "idna>=2.0.0"],
        "socks": ["PySocks!=1.5.7,>=1.5.6"],
        'socks:sys_platform == "win32" and python_version == "2.7"': ["win-inet-pton"],
    }
    expected_python_requires = ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*"

    assert expected_name == result["name"]
    assert expected_version == result["version"]
    assert expected_install_requires == result["install_requires"]
    assert expected_extras_require == result["extras_require"]
    assert expected_python_requires == result["python_requires"]


def test_setup_reader_read_sub_level_setup_call_with_direct_types(setup):
    result = SetupReader.read_from_pep517_hook(setup("sqlalchemy"))

    expected_name = "SQLAlchemy"
    expected_version = "1.2.3"
    expected_install_requires = []
    expected_extras_require = {
        "mysql": ["mysqlclient"],
        "pymysql": ["pymysql"],
        "postgresql": ["psycopg2"],
        "postgresql_pg8000": ["pg8000"],
        "postgresql_psycopg2cffi": ["psycopg2cffi"],
        "oracle": ["cx-oracle"],
        "mssql_pyodbc": ["pyodbc"],
        "mssql_pymssql": ["pymssql"],
    }

    assert expected_name == result["name"]
    assert expected_version == result["version"]
    assert expected_install_requires == result["install_requires"]
    assert expected_extras_require == result["extras_require"]
    assert result["python_requires"] is None


def test_setup_reader_read_setup_cfg(setup):
    result = SetupReader.read_from_pep517_hook(setup("with-setup-cfg"))

    expected_name = "with-setup-cfg"
    expected_version = "1.2.3"
    expected_install_requires = ["six", "tomlkit"]
    expected_extras_require = {
        "validation": ["cerberus"],
        "tests": ["pytest", "pytest-xdist", "pytest-cov"],
    }
    expected_python_requires = ">=2.6,!=3.0,!=3.1,!=3.2,!=3.3"

    assert expected_name == result["name"]
    assert expected_version == result["version"]
    assert expected_install_requires == result["install_requires"]
    assert expected_extras_require == result["extras_require"]
    assert sorted(expected_python_requires.split(",")) == sorted(
        result["python_requires"].split(",")
    )


def test_setup_reader_read_setup_kwargs(setup):
    result = SetupReader.read_from_pep517_hook(setup("pendulum"))

    expected_name = "pendulum"
    expected_version = "2.0.4"
    expected_install_requires = ["python-dateutil<3.0,>=2.6", "pytzdata>=2018.3"]
    expected_extras_require = {'typing:python_version < "3.5"': ["typing<4.0,>=3.6"]}
    expected_python_requires = ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*"

    assert expected_name == result["name"]
    assert expected_version == result["version"]
    assert expected_install_requires == result["install_requires"]
    assert expected_extras_require == result["extras_require"]
    assert expected_python_requires == result["python_requires"]


def test_setup_reader_read_extras_require_with_variables(setup):
    result = SetupReader.read_from_pep517_hook(setup("extras_require_with_vars"))

    expected_name = "extras-require-with-vars"
    expected_version = "0.0.1"
    expected_install_requires = []
    expected_extras_require = {"test": ["pytest"]}
    expected_python_requires = None

    assert expected_name == result["name"]
    assert expected_version == result["version"]
    assert expected_install_requires == result["install_requires"]
    assert expected_extras_require == result["extras_require"]
    assert expected_python_requires == result["python_requires"]


def test_setup_reader_setuptools(setup):
    result = SetupReader.read_from_pep517_hook(setup("setuptools_setup"))

    expected_name = "my-package"
    expected_version = "0.1.2"

    assert expected_name == result["name"]
    assert expected_version == result["version"]
