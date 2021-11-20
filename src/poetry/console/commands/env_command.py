from typing import TYPE_CHECKING
from typing import Optional

from poetry.console.commands.command import Command


if TYPE_CHECKING:
    from poetry.utils.env import Env


class EnvCommand(Command):
    def __init__(self) -> None:
        self._env = None

        super().__init__()

    @property
    def env(self) -> Optional["Env"]:
        return self._env

    def set_env(self, env: "Env") -> None:
        self._env = env
