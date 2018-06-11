import os
import re
import sys
import traceback

from cleo import Application as BaseApplication
from cleo.formatters import Formatter
from cleo.inputs import ArgvInput
from cleo.outputs import ConsoleOutput
from cleo.outputs import Output

from poetry import __version__

from poetry.io.raw_argv_input import RawArgvInput

from .commands import AboutCommand
from .commands import AddCommand
from .commands import BuildCommand
from .commands import CheckCommand
from .commands import ConfigCommand
from .commands import DevelopCommand
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

from .commands.cache import CacheClearCommand

from .commands.debug import DebugInfoCommand
from .commands.debug import DebugResolveCommand

from .commands.self import SelfUpdateCommand


class Application(BaseApplication):
    def __init__(self):
        super(Application, self).__init__("Poetry", __version__)

        self._poetry = None
        self._skip_io_configuration = False
        self._formatter = Formatter(True)
        self._formatter.add_style("error", "red", options=["bold"])

    @property
    def poetry(self):
        from poetry.poetry import Poetry

        if self._poetry is not None:
            return self._poetry

        self._poetry = Poetry.create(os.getcwd())

        return self._poetry

    def reset_poetry(self):  # type: () -> None
        self._poetry = None

    def run(self, i=None, o=None):  # type: (...) -> int
        if i is None:
            i = ArgvInput()

        if o is None:
            o = ConsoleOutput()

            self._formatter.with_colors(o.is_decorated())
            o.set_formatter(self._formatter)

        name = i.get_first_argument()
        if name in ["run", "script"]:
            self._skip_io_configuration = True
            i = RawArgvInput()

        return super(Application, self).run(i, o)

    def do_run(self, i, o):
        name = self.get_command_name(i)

        if name not in ["run", "script"]:
            return super(Application, self).do_run(i, o)

        command = self.find(name)

        self._running_command = command
        status_code = command.run(i, o)
        self._running_command = None

        return status_code

    def configure_io(self, i, o):
        if self._skip_io_configuration:
            return

        super(Application, self).configure_io(i, o)

    def get_default_commands(self):  # type: () -> list
        commands = super(Application, self).get_default_commands()

        commands += [
            AboutCommand(),
            AddCommand(),
            BuildCommand(),
            CheckCommand(),
            ConfigCommand(),
            DevelopCommand(),
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
        commands += [CacheClearCommand()]

        # Debug commands
        commands += [DebugInfoCommand(), DebugResolveCommand()]

        # Self commands
        commands += [SelfUpdateCommand()]

        return commands

    def render_exception(self, e, o):
        tb = traceback.extract_tb(sys.exc_info()[2])

        title = "[<error>%s</error>]  " % e.__class__.__name__
        l = len(title)
        width = self._terminal.width
        if not width:
            width = sys.maxsize

        formatter = o.get_formatter()
        lines = []
        for line in re.split("\r?\n", str(e)):
            for splitline in [
                line[x : x + (width - 4)] for x in range(0, len(line), width - 4)
            ]:
                line_length = (
                    len(re.sub("\[[^m]*m", "", formatter.format(splitline))) + 4
                )
                lines.append((splitline, line_length))

                l = max(line_length, l)

        messages = []
        empty_line = formatter.format("%s" % (" " * l))
        messages.append(empty_line)
        messages.append(
            formatter.format("%s%s" % (title, " " * max(0, l - len(title))))
        )

        for line in lines:
            messages.append(
                formatter.format(
                    "<error>%s  %s</error>" % (line[0], " " * (l - line[1]))
                )
            )

        messages.append(empty_line)

        o.writeln(messages, Output.OUTPUT_RAW)

        if Output.VERBOSITY_VERBOSE <= o.get_verbosity():
            o.writeln("<comment>Exception trace:</comment>")

            for exc_info in tb:
                file_ = exc_info[0]
                line_number = exc_info[1]
                function = exc_info[2]
                line = exc_info[3]

                o.writeln(
                    " <info>%s</info> in <fg=cyan>%s()</> "
                    "at line <info>%s</info>" % (file_, function, line_number)
                )
                o.writeln("   %s" % line)

            o.writeln("")

        if self._running_command is not None:
            o.writeln("<info>%s</info>" % self._running_command.get_synopsis())

            o.writeln("")
