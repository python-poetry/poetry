from __future__ import annotations

from poetry.console.commands.self.self_command import SelfCommand
from poetry.console.commands.source.remove import SourceRemoveCommand


class SelfSourceRemoveCommand(SelfCommand, SourceRemoveCommand):
    name = "self source remove"
    description = "Removes sources from Poetry's runtime environment."
    options = [o for o in SourceRemoveCommand.options if o.name in {"name"}]
    help = f"""\
The <c1>self source remove</c1> command removes sources from Poetry's runtime \
environment.

This is managed in the <comment>{SelfCommand.get_default_system_pyproject_file()}</> \
file.
"""
