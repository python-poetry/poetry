import os

from cleo import Application as BaseApplication

from poetry.poetry import Poetry
from poetry.utils.venv import Venv

from .commands import AboutCommand
from .commands import AddCommand
from .commands import InstallCommand
from .commands import LockCommand
from .commands import NewCommand
from .commands import RemoveCommand
from .commands import ShowCommand
from .commands import UpdateCommand


class Application(BaseApplication):

    def __init__(self):
        super().__init__('Poetry', Poetry.VERSION)

        self._poetry = None
        self._venv = Venv.create()

    @property
    def poetry(self) -> Poetry:
        if self._poetry is not None:
            return self._poetry

        self._poetry = Poetry.create(os.getcwd())

        return self._poetry

    def reset_poetry(self) -> None:
        self._poetry = None

    @property
    def venv(self) -> Venv:
        return self._venv

    def get_default_commands(self) -> list:
        commands = super(Application, self).get_default_commands()

        return commands + [
            AboutCommand(),
            AddCommand(),
            InstallCommand(),
            LockCommand(),
            NewCommand(),
            RemoveCommand(),
            ShowCommand(),
            UpdateCommand(),
        ]

    def do_run(self, i, o) -> int:
        if self._venv.is_venv() and o.is_debug():
            o.writeln(f'Using virtualenv: <comment>{self._venv.venv}</>')

        return super().do_run(i, o)
