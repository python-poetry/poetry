from ..command import Command
from .info import DebugInfoCommand
from .resolve import DebugResolveCommand


class DebugCommand(Command):

    name = "debug"
    description = "Debug various elements of Poetry."

    commands = [DebugInfoCommand().default(), DebugResolveCommand()]
