from typing import TYPE_CHECKING

from .command import Command


if TYPE_CHECKING:
    from poetry.utils.env import Env


class EnvCommand(Command):
    def __init__(self) -> None:
        self._env = None

        super(EnvCommand, self).__init__()

    @property
    def env(self) -> "Env":
        return self._env

    def set_env(self, env: "Env") -> None:
        self._env = env
