import pytest
from poetry.utils.helpers import parse_requires,\
    __expand_env_vars


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

[:(python_version >= "2.7.0.0" and python_version < "2.8.0.0") or (python_version >= "3.4.0.0" and python_version < "3.5.0.0")]
typing>=3.6.0.0,<4.0.0.0

[:python_version >= "2.7.0.0" and python_version < "2.8.0.0"]
virtualenv>=15.2.0.0,<16.0.0.0
pathlib2>=2.3.0.0,<3.0.0.0

[:python_version >= "3.4.0.0" and python_version < "3.6.0.0"]
zipfile36>=0.1.0.0,<0.2.0.0    
"""
    result = parse_requires(requires)
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
        'typing>=3.6.0.0,<4.0.0.0; (python_version >= "2.7.0.0" and python_version < "2.8.0.0") or (python_version >= "3.4.0.0" and python_version < "3.5.0.0")',
        'virtualenv>=15.2.0.0,<16.0.0.0; python_version >= "2.7.0.0" and python_version < "2.8.0.0"',
        'pathlib2>=2.3.0.0,<3.0.0.0; python_version >= "2.7.0.0" and python_version < "2.8.0.0"',
        'zipfile36>=0.1.0.0,<0.2.0.0; python_version >= "3.4.0.0" and python_version < "3.6.0.0"',
    ]
    assert result == expected


@pytest.fixture(scope="module")
def simple_env_var():
    import os
    env_var_name = "__POETRY_ENV_TEST"
    env_var_value = "deadbeef"
    os.environ[env_var_name] = env_var_value
    
    yield (env_var_name, env_var_value)
    del os.environ[env_var_name] # only guaranteed to work on some platforms!


def test_string_env_var_expansion(simple_env_var):
    (var_name, var_value) = simple_env_var

    x = "${" + var_name + "}"
    res = __expand_env_vars(x)
    assert res == var_value


def test_dict_env_var_expansion(simple_env_var):
    (var_name, var_value) = simple_env_var

    x = {"key": "${" + var_name + "}"}
    res = __expand_env_vars(x)
    assert res['key'] == var_value


def test_list_env_var_expansion(simple_env_var):
    (var_name, var_value) = simple_env_var

    x = ["${" + var_name + "}"]*2
    res = __expand_env_vars(x)

    assert res == [var_value, var_value]


def test_list_nested_dict_env_var_expansion(simple_env_var):
    (var_name, var_value) = simple_env_var

    x = {'key': ["${" + var_name + "}"]*2}
    res = __expand_env_vars(x)

    assert res['key'] == [var_value, var_value]
