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
