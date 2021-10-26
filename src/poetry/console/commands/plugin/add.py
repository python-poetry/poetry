import os

from typing import TYPE_CHECKING

from cleo.helpers import argument
from cleo.helpers import option

from poetry.console.commands.init import InitCommand
from poetry.console.commands.plugin.plugin_command_mixin import PluginCommandMixin


if TYPE_CHECKING:
    from poetry.console.application import Application  # noqa
    from poetry.console.commands.update import UpdateCommand  # noqa


class PluginAddCommand(InitCommand, PluginCommandMixin):

    name = "plugin add"

    description = "Adds new plugins."

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

    help = """
The <c1>plugin add</c1> command installs Poetry plugins globally.

It works similarly to the <c1>add</c1> command:

If you do not specify a version constraint, poetry will choose a suitable one based on the available package versions.

You can specify a package in the following forms:

  - A single name (<b>requests</b>)
  - A name and a constraint (<b>requests@^2.23.0</b>)
  - A git url (<b>git+https://github.com/python-poetry/poetry.git</b>)
  - A git url with a revision (<b>git+https://github.com/python-poetry/poetry.git#develop</b>)
  - A git SSH url (<b>git+ssh://github.com/python-poetry/poetry.git</b>)
  - A git SSH url with a revision (<b>git+ssh://github.com/python-poetry/poetry.git#develop</b>)
  - A file path (<b>../my-package/my-package.whl</b>)
  - A directory (<b>../my-package/</b>)
  - A url (<b>https://example.com/packages/my-package-0.1.0.tar.gz</b>)\
"""

    def handle(self) -> int:
        from pathlib import Path

        import tomlkit

        from poetry.core.semver.helpers import parse_constraint

        from poetry.factory import Factory
        from poetry.utils.env import EnvManager
        from poetry.utils.helpers import canonicalize_name

        requested_plugins = self.argument("plugins")

        # Plugins should be installed in the system env to be globally available
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

        installed_plugins = {
            canonicalize_name(ep.distro.name) for ep in self.get_plugin_entry_points()
        }

        # We check for the plugins existence first.
        plugins = []
        skipped_plugins = []
        parsed_plugins = self._parse_requirements(requested_plugins)
        for i, plugin in enumerate(parsed_plugins):
            plugin_name = canonicalize_name(plugin.pop("name"))
            if plugin_name in installed_plugins:
                if plugin_name not in existing_plugins:
                    existing_plugins[plugin_name] = plugin

                if not plugin:
                    skipped_plugins.append(plugin_name)

                    continue

            plugins.append(canonicalize_name(requested_plugins[i]))

        if skipped_plugins:
            self.line(
                "The following plugins are already present and will be skipped:\n"
            )
            for name in sorted(skipped_plugins):
                self.line(f"  • <c1>{name}</c1>")

            self.line(
                "\nIf you want to upgrade it to the latest compatible version, "
                "you can use `poetry plugin add plugin@latest.\n"
            )

        if not plugins:
            return 0

        plugins = self._determine_requirements(plugins)

        # We add the plugins to the plugins.toml file
        plugin_names = []
        for plugin in plugins:
            if "version" in plugin:
                # Validate version constraint
                parse_constraint(plugin["version"])

            constraint = tomlkit.inline_table()
            for name, value in plugin.items():
                if name == "name":
                    continue

                constraint[name] = value

            if len(constraint) == 1 and "version" in constraint:
                constraint = constraint["version"]

            root_package.add_dependency(
                Factory.create_dependency(plugin["name"], constraint)
            )

            existing_plugins[plugin["name"]] = constraint
            plugin_names.append(plugin["name"])

        return_code = self.update(
            system_env, root_package, self._io, whitelist=plugin_names
        )

        if return_code != 0 or self.option("dry-run"):
            return return_code

        env_dir.joinpath("plugins.toml").write_text(
            tomlkit.dumps(existing_plugins, sort_keys=True), encoding="utf-8"
        )

        return 0
