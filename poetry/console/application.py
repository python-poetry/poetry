from cleo import Application as BaseApplication

from poetry import __version__

from .commands.about import AboutCommand
from .commands.add import AddCommand
from .commands.build import BuildCommand
from .commands.cache.cache import CacheCommand
from .commands.check import CheckCommand
from .commands.config import ConfigCommand
from .commands.debug.debug import DebugCommand
from .commands.env.env import EnvCommand
from .commands.export import ExportCommand
from .commands.init import InitCommand
from .commands.install import InstallCommand
from .commands.lock import LockCommand
from .commands.new import NewCommand
from .commands.publish import PublishCommand
from .commands.remove import RemoveCommand
from .commands.run import RunCommand
from .commands.search import SearchCommand
from .commands.self.self import SelfCommand
from .commands.shell import ShellCommand
from .commands.show import ShowCommand
from .commands.update import UpdateCommand
from .commands.version import VersionCommand
from .config import ApplicationConfig


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
        from poetry.factory import Factory
        from poetry.utils._compat import Path

        if self._poetry is not None:
            return self._poetry

        self._poetry = Factory().create_poetry(Path.cwd())

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
            ExportCommand(),
            InitCommand(),
            InstallCommand(),
            LockCommand(),
            NewCommand(),
            PublishCommand(),
            RemoveCommand(),
            RunCommand(),
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
