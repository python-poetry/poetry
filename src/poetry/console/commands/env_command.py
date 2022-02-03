from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.console.commands.command import Command


if TYPE_CHECKING:
    from poetry.utils.env import Env


class EnvCommand(Command):
    def __init__(self) -> None:
        # Set in poetry.console.application.Application.configure_installer
        self._env: Env = None  # type: ignore[assignment]

        super().__init__()

    @property
    def env(self) -> Env:
        return self._env

    def set_env(self, env: Env) -> None:
        self._env = env
