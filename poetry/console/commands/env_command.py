from typing import Optional

from poetry.utils.env import Env

from .command import Command


class EnvCommand(Command):
    def __init__(self) -> None:
        self._env = None

        super(EnvCommand, self).__init__()

    @property
    def env(self) -> Optional[Env]:
        return self._env

    def set_env(self, env: Env) -> None:
        self._env = env
