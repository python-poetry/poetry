from __future__ import annotations

from poetry.console.commands.self.self_command import SelfCommand
from poetry.console.commands.source.add import SourceAddCommand


class SelfSourceAddCommand(SelfCommand, SourceAddCommand):
    name = "self source add"
    description = "Add additional sources to Poetry's runtime environment."
    options = [
        o for o in SourceAddCommand.options if o.name in {"default", "secondary"}
    ]
    help = f"""\
The <c1>self source add</c1> command adds additional sources to Poetry's runtime \
environment.

This is managed in the <comment>{SelfCommand.get_default_system_pyproject_file()}</> \
file.
"""
