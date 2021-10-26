import os

from typing import TYPE_CHECKING

from cleo.helpers import argument
from cleo.helpers import option

from poetry.console.commands.command import Command

from .plugin_command_mixin import PluginCommandMixin


if TYPE_CHECKING:
    from poetry.console.application import Application  # noqa


class PluginRemoveCommand(Command, PluginCommandMixin):

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

        import tomlkit

        from poetry.utils.env import EnvManager
        from poetry.utils.helpers import canonicalize_name

        plugins = self.argument("plugins")

        system_env = EnvManager.get_system_env(naive=True)
        env_dir = Path(
            os.getenv("POETRY_HOME") if os.getenv("POETRY_HOME") else system_env.path
        )

        existing_plugins = {}
        if env_dir.joinpath("plugins.toml").exists():
            existing_plugins = tomlkit.loads(
                env_dir.joinpath("plugins.toml").read_text(encoding="utf-8")
            )

        root_package = self.create_env_package(system_env, existing_plugins)

        entrypoints = self.get_plugin_entry_points()

        removed_plugins = []
        for plugin in plugins:
            plugin = canonicalize_name(plugin)
            is_plugin = False
            installed = False
            for entrypoint in entrypoints:
                if canonicalize_name(entrypoint.distro.name) == plugin:
                    is_plugin = True
                    break

            for i, dependency in enumerate(root_package.requires):
                if dependency.name == plugin:
                    installed = True

                    break

            if not installed:
                self.line_error(f"<warning>Plugin {plugin} is not installed.</warning>")

                continue

            if not is_plugin:
                self.line_error(
                    f"<warning>The package {plugin} is not a plugin.</<warning>"
                )
                continue

            if plugin in existing_plugins:
                del existing_plugins[plugin]

            removed_plugins.append(plugin)

        if not removed_plugins:
            return 1

        _root_package = root_package
        root_package = root_package.with_dependency_groups([], only=True)
        for dependency in _root_package.requires:
            if dependency.name not in removed_plugins:
                root_package.add_dependency(dependency)

        return_code = self.update(
            system_env,
            root_package,
            self._io,
            whitelist=removed_plugins,
        )

        if return_code != 0 or self.option("dry-run"):
            return return_code

        env_dir.joinpath("plugins.toml").write_text(
            tomlkit.dumps(existing_plugins, sort_keys=True), encoding="utf-8"
        )

        return 0
