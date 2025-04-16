from __future__ import annotations

from poetry.console.commands.env.activate import EnvActivateCommand


class ActivateCommand(EnvActivateCommand):
    name = "activate"
    description = "Alias for the env activate command"
