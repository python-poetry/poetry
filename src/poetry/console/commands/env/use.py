from __future__ import annotations

from cleo.helpers import argument

from poetry.console.commands.command import Command


class EnvUseCommand(Command):
    name = "env use"
    description = "Activates or creates a new virtualenv for the current project."

    arguments = [argument("python", "The python executable to use.")]

    def handle(self) -> int:
        from poetry.utils.env import EnvManager

        manager = EnvManager(self.poetry, io=self.io)

        if self.argument("python") == "system":
            manager.deactivate()

            return 0

        env = manager.activate(self.argument("python"))

        self.line(f"Using virtualenv: <comment>{env.path}</>")

        return 0
