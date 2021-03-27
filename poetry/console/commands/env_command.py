from typing import TYPE_CHECKING

from .command import Command


if TYPE_CHECKING:
    from poetry.utils.env import VirtualEnv


class EnvCommand(Command):
    def __init__(self) -> None:
        self._env = None

        super(EnvCommand, self).__init__()

    @property
    def env(self) -> "VirtualEnv":
        return self._env

    def set_env(self, env: "VirtualEnv") -> None:
        self._env = env
