from __future__ import annotations

import runpy

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_module_entrypoint_exits_with_application_status(mocker: MockerFixture) -> None:
    main_mock = mocker.patch("poetry.console.application.main", side_effect=lambda: 17)

    with pytest.raises(SystemExit) as e:
        runpy.run_module("poetry", run_name="__main__")

    assert e.value.code == 17
    assert main_mock.call_count == 1
