from cleo.helpers import argument

from poetry.console.commands.command import Command


class EnvUseCommand(Command):

    name = "env use"
    description = "Activates or creates a new virtualenv for the current project."

    arguments = [argument("python", "The python executable to use.")]

    def handle(self) -> None:
        from poetry.utils.env import EnvManager

        manager = EnvManager(self.poetry)

        if self.argument("python") == "system":
            manager.deactivate(self._io)

            return

        env = manager.activate(self.argument("python"), self._io)

        self.line(f"Using virtualenv: <comment>{env.path}</>")
