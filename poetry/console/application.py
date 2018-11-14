import os

from cleo import Application as BaseApplication

from poetry import __version__

from .commands import AboutCommand
from .commands import AddCommand
from .commands import BuildCommand
from .commands import CheckCommand
from .commands import ConfigCommand
from .commands import DevelopCommand
from .commands import ExportCommand
from .commands import InitCommand
from .commands import InstallCommand
from .commands import LockCommand
from .commands import NewCommand
from .commands import PublishCommand
from .commands import RemoveCommand
from .commands import RunCommand
from .commands import ScriptCommand
from .commands import SearchCommand
from .commands import ShellCommand
from .commands import ShowCommand
from .commands import UpdateCommand
from .commands import VersionCommand

from .commands.debug import DebugCommand

from .commands.cache import CacheCommand

from .commands.self import SelfCommand

from .config import ApplicationConfig

from .commands.env import EnvCommand


class Application(BaseApplication):
    def __init__(self):
        super(Application, self).__init__(
            "poetry", __version__, config=ApplicationConfig("poetry", __version__)
        )

        self._poetry = None

        for command in self.get_default_commands():
            self.add(command)

    @property
    def poetry(self):
        from poetry.poetry import Poetry

        if self._poetry is not None:
            return self._poetry

        self._poetry = Poetry.create(os.getcwd())

        return self._poetry

    def reset_poetry(self):  # type: () -> None
        self._poetry = None

    def get_default_commands(self):  # type: () -> list
        commands = [
            AboutCommand(),
            AddCommand(),
            BuildCommand(),
            CheckCommand(),
            ConfigCommand(),
            DevelopCommand(),
            ExportCommand(),
            InitCommand(),
            InstallCommand(),
            LockCommand(),
            NewCommand(),
            PublishCommand(),
            RemoveCommand(),
            RunCommand(),
            ScriptCommand(),
            SearchCommand(),
            ShellCommand(),
            ShowCommand(),
            UpdateCommand(),
            VersionCommand(),
        ]

        # Cache commands
        commands += [CacheCommand()]

        # Debug command
        commands += [DebugCommand()]

        # Env command
        commands += [EnvCommand()]

        # Self commands
        commands += [SelfCommand()]

        return commands


if __name__ == "__main__":
    Application().run()
