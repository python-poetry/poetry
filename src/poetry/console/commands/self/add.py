from __future__ import annotations

from poetry.console.commands.add import AddCommand
from poetry.console.commands.self.self_command import SelfCommand


class SelfAddCommand(SelfCommand, AddCommand):
    name = "self add"
    description = "Add additional packages to Poetry's runtime environment."
    options = [
        o
        for o in AddCommand.options
        if o.name in {"editable", "extras", "source", "dry-run", "allow-prereleases"}
    ]
    help = f"""\
The <c1>self add</c1> command installs additional package's to Poetry's runtime \
environment.

This is managed in the <comment>{SelfCommand.get_default_system_pyproject_file()}</> \
file.

{AddCommand.examples}
"""
