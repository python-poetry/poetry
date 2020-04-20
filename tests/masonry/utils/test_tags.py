import pytest

from poetry.masonry.utils.tags import get_abi_tag
from poetry.utils.env import MockEnv


def test_tags_cpython38():
    assert (
        get_abi_tag(
            MockEnv(
                version_info=(3, 8, 0),
                python_implementation="CPython",
                config_vars={"Py_DEBUG": True},
            )
        )
        == "cp38d"
    )
    assert (
        get_abi_tag(
            MockEnv(
                version_info=(3, 8, 0), python_implementation="CPython", config_vars={},
            )
        )
        == "cp38"
    )


def test_tags_cpython37():
    assert (
        get_abi_tag(
            MockEnv(
                version_info=(3, 7, 3),
                python_implementation="CPython",
                config_vars={"Py_DEBUG": True, "WITH_PYMALLOC": True},
            )
        )
        == "cp37dm"
    )
    assert (
        get_abi_tag(
            MockEnv(
                version_info=(3, 7, 3),
                python_implementation="CPython",
                config_vars={"Py_DEBUG": True, "WITH_PYMALLOC": False},
            )
        )
        == "cp37d"
    )
    assert (
        get_abi_tag(
            MockEnv(
                version_info=(3, 7, 3),
                python_implementation="CPython",
                config_vars={"Py_DEBUG": False, "WITH_PYMALLOC": True},
            )
        )
        == "cp37m"
    )
    assert (
        get_abi_tag(
            MockEnv(
                version_info=(3, 7, 3),
                python_implementation="CPython",
                config_vars={"Py_DEBUG": False, "WITH_PYMALLOC": False},
            )
        )
        == "cp37"
    )
    with pytest.warns(RuntimeWarning):
        assert (
            get_abi_tag(
                MockEnv(
                    version_info=(3, 7, 3),
                    python_implementation="CPython",
                    config_vars={"Py_DEBUG": False},
                )
            )
            == "cp37m"
        )
