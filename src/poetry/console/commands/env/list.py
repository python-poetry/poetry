from __future__ import annotations

from cleo.helpers import option

from poetry.console.commands.command import Command


class EnvListCommand(Command):
    name = "env list"
    description = "Lists all virtualenvs associated with the current project."

    options = [option("full-path", None, "Output the full paths of the virtualenvs.")]

    def handle(self) -> int:
        from poetry.utils.env import EnvManager

        manager = EnvManager(self.poetry)
        current_env = manager.get()

        for venv in manager.list():
            name = venv.path.name
            if self.option("full-path"):
                name = str(venv.path)

            if venv == current_env:
                self.line(f"<info>{name} (Activated)</info>")

                continue

            self.line(name)

        return 0
