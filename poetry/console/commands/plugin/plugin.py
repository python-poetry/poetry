from ..command import Command
from .install import PluginInstallCommand


class PluginCommand(Command):

    name = "plugin"
    description = "Manage Poetry's plugins."

    commands = [PluginInstallCommand()]
