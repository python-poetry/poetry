from ..command import Command
from .info import DebugInfoCommand
from .resolve import DebugResolveCommand


class DebugCommand(Command):
    """
    Debug various elements of Poetry.

    debug
    """

    commands = [DebugInfoCommand().default(), DebugResolveCommand()]
