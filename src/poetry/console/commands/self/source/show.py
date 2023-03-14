from __future__ import annotations

from poetry.console.commands.self.self_command import SelfCommand
from poetry.console.commands.source.show import SourceShowCommand


class SelfSourceShowCommand(SelfCommand, SourceShowCommand):
    name = "self source show"
    description = "Show sources in Poetry's runtime environment."
    options = [o for o in SourceShowCommand.options if o.name in {"source"}]
    help = f"""\
The <c1>self source show</c1> command shows sources from Poetry's runtime \
environment.

This is managed in the <comment>{SelfCommand.get_default_system_pyproject_file()}</> \
file.
"""
