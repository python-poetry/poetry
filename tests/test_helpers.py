from __future__ import annotations

import os

from tests.helpers import flatten_dict
from tests.helpers import isolated_environment
from tests.helpers import pbs_installer_supported_arch


def test_flatten_dict() -> None:
    orig_dict = {
        "a": 1,
        "b": 2,
        "c": {
            "x": 8,
            "y": 9,
        },
    }

    flattened_dict = {
        "a": 1,
        "b": 2,
        "c:x": 8,
        "c:y": 9,
    }

    assert flattened_dict == flatten_dict(orig_dict, delimiter=":")


def test_isolated_environment_restores_original_environ() -> None:
    original_environ = dict(os.environ)
    with isolated_environment():
        os.environ["TEST_VAR"] = "test"
    assert os.environ == original_environ


def test_isolated_environment_clears_environ() -> None:
    os.environ["TEST_VAR"] = "test"
    with isolated_environment(clear=True):
        assert "TEST_VAR" not in os.environ
    assert "TEST_VAR" in os.environ


def test_isolated_environment_updates_environ() -> None:
    with isolated_environment(environ={"NEW_VAR": "new_value"}):
        assert os.environ["NEW_VAR"] == "new_value"
    assert "NEW_VAR" not in os.environ

#---------------------2 new tests-----------------------

def test_pbs_installer_supported_arch_accepts_supported_archs() -> None:
    assert pbs_installer_supported_arch("x86_64") is True
    assert pbs_installer_supported_arch("amd64") is True
    assert pbs_installer_supported_arch("arm64") is True


def test_pbs_installer_supported_arch_rejects_unsupported_archs() -> None:
    assert pbs_installer_supported_arch("sparc") is False
    assert pbs_installer_supported_arch("mips") is False
