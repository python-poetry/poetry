from collections import defaultdict
from typing import TYPE_CHECKING
from typing import DefaultDict
from typing import Dict
from typing import List
from typing import Union

from poetry.console.commands.command import Command
from poetry.console.commands.plugin.plugin_command_mixin import PluginCommandMixin


if TYPE_CHECKING:
    from poetry.core.packages.package import Package


class PluginShowCommand(Command, PluginCommandMixin):

    name = "plugin show"

    description = "Shows information about the currently installed plugins."

    def handle(self) -> int:
        from poetry.plugins.application_plugin import ApplicationPlugin
        from poetry.repositories.installed_repository import InstalledRepository
        from poetry.utils.env import EnvManager
        from poetry.utils.helpers import canonicalize_name
        from poetry.utils.helpers import pluralize

        plugins: DefaultDict[str, Dict[str, Union["Package", List[str]]]] = defaultdict(
            lambda: {
                "package": None,
                "plugins": [],
                "application_plugins": [],
            }
        )

        entry_points = self.get_plugin_entry_points()

        system_env = EnvManager.get_system_env(naive=True)
        installed_repository = InstalledRepository.load(
            system_env, with_dependencies=True
        )

        packages_by_name = {pkg.name: pkg for pkg in installed_repository.packages}

        for entry_point in entry_points:
            plugin = entry_point.load()
            category = "plugins"
            if issubclass(plugin, ApplicationPlugin):
                category = "application_plugins"

            package = packages_by_name[canonicalize_name(entry_point.distro.name)]
            plugins[package.pretty_name]["package"] = package
            plugins[package.pretty_name][category].append(entry_point)

        for name, info in plugins.items():
            package = info["package"]
            description = " " + package.description if package.description else ""
            self.line("")
            self.line(f"  • <c1>{name}</c1> (<c2>{package.version}</c2>){description}")
            provide_line = "     "
            if info["plugins"]:
                count = len(info["plugins"])
                provide_line += f" <info>{count}</info> plugin{pluralize(count)}"

            if info["application_plugins"]:
                if info["plugins"]:
                    provide_line += " and"

                count = len(info["application_plugins"])
                provide_line += (
                    f" <info>{count}</info> application plugin{pluralize(count)}"
                )

            self.line(provide_line)

            if package.requires:
                self.line("")
                self.line("      <info>Dependencies</info>")
                for dependency in package.requires:
                    self.line(
                        f"        - {dependency.pretty_name} (<c2>{dependency.pretty_constraint}</c2>)"
                    )

        return 0
