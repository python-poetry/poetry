from typing import TYPE_CHECKING

from .command import Command


if TYPE_CHECKING:
    from poetry.utils.env import VirtualEnv  # noqa


class EnvCommand(Command):
    def __init__(self):  # type: () -> None
        self._env = None

        super(EnvCommand, self).__init__()

    @property
    def env(self):  # type: () -> "VirtualEnv"
        return self._env

    def set_env(self, env):  # type: ("VirtualEnv") -> None
        self._env = env
