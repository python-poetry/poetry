import os

from typing import TYPE_CHECKING
from typing import cast

from cleo.helpers import argument
from cleo.helpers import option

from poetry.console.commands.command import Command


if TYPE_CHECKING:
    from poetry.console.application import Application  # noqa
    from poetry.console.commands.remove import RemoveCommand


class PluginRemoveCommand(Command):

    name = "plugin remove"

    description = "Removes installed plugins"

    arguments = [
        argument("plugins", "The names of the plugins to install.", multiple=True),
    ]

    options = [
        option(
            "dry-run",
            None,
            "Output the operations but do not execute anything (implicitly enables --verbose).",
        )
    ]

    def handle(self) -> int:
        from pathlib import Path

        from cleo.io.inputs.string_input import StringInput
        from cleo.io.io import IO

        from poetry.factory import Factory
        from poetry.utils.env import EnvManager

        plugins = self.argument("plugins")

        system_env = EnvManager.get_system_env(naive=True)
        env_dir = Path(
            os.getenv("POETRY_HOME") if os.getenv("POETRY_HOME") else system_env.path
        )

        # From this point forward, all the logic will be deferred to
        # the remove command, by using the global `pyproject.toml` file.
        application = cast("Application", self.application)
        remove_command: "RemoveCommand" = cast(
            "RemoveCommand", application.find("remove")
        )
        # We won't go through the event dispatching done by the application
        # so we need to configure the command manually
        remove_command.set_poetry(Factory().create_poetry(env_dir))
        remove_command.set_env(system_env)
        application._configure_installer(remove_command, self._io)

        argv = ["remove"] + plugins
        if self.option("dry-run"):
            argv.append("--dry-run")

        return remove_command.run(
            IO(
                StringInput(" ".join(argv)),
                self._io.output,
                self._io.error_output,
            )
        )
