from __future__ import annotations

import runpy

import pytest


def test_module_entrypoint_exits_with_application_status(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[None] = []

    def main() -> int:
        calls.append(None)
        return 17

    monkeypatch.setattr("poetry.console.application.main", main)

    with pytest.raises(SystemExit) as e:
        runpy.run_module("poetry", run_name="__main__", alter_sys=True)

    assert e.value.code == 17
    assert calls == [None]
