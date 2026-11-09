from __future__ import annotations

import pytest

from cleo.commands.command import Command
from cleo.exceptions import CleoLogicError

from poetry.console.command_loader import CommandLoader


class _DummyCommand(Command):
    name = "dummy"


class _OtherCommand(Command):
    name = "other"


def test_register_factory_adds_new_command() -> None:
    loader = CommandLoader({})

    loader.register_factory("dummy", _DummyCommand)

    assert loader.has("dummy")
    assert isinstance(loader.get("dummy"), _DummyCommand)


def test_register_factory_rejects_duplicate() -> None:
    loader = CommandLoader({"dummy": _DummyCommand})

    with pytest.raises(CleoLogicError, match="dummy"):
        loader.register_factory("dummy", _OtherCommand)

    # The originally registered factory must not have been replaced.
    assert isinstance(loader.get("dummy"), _DummyCommand)
