from collections import defaultdict
from typing import TYPE_CHECKING
from typing import DefaultDict
from typing import Dict
from typing import List
from typing import Union

from poetry.console.commands.command import Command


if TYPE_CHECKING:
    from poetry.core.packages.package import Package


class PluginShowCommand(Command):

    name = "plugin show"

    description = "Shows information about the currently installed plugins."

    def handle(self) -> int:
        from poetry.plugins.application_plugin import ApplicationPlugin
        from poetry.plugins.plugin_manager import PluginManager
        from poetry.repositories.installed_repository import InstalledRepository
        from poetry.utils.env import EnvManager
        from poetry.utils.helpers import canonicalize_name

        plugins: DefaultDict[str, Dict[str, Union["Package", List[str]]]] = defaultdict(
            lambda: {
                "package": None,
                "plugins": [],
                "application_plugins": [],
            }
        )

        entry_points = (
            PluginManager("application.plugin").get_plugin_entry_points()
            + PluginManager("plugin").get_plugin_entry_points()
        )

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

            package = packages_by_name[canonicalize_name(entry_point.name)]
            plugins[package.pretty_name]["package"] = package
            plugins[package.pretty_name][category].append(entry_point)

        for name, info in plugins.items():
            package = info["package"]
            self.line("")
            self.line(
                "  • <c1>{}</c1> (<c2>{}</c2>){}".format(
                    name,
                    package.version,
                    " " + package.description if package.description else "",
                )
            )
            provide_line = "     "
            if info["plugins"]:
                provide_line += " <info>{}</info> plugin{}".format(
                    len(info["plugins"]), "s" if len(info["plugins"]) > 1 else ""
                )

            if info["application_plugins"]:
                if info["plugins"]:
                    provide_line += " and"

                provide_line += " <info>{}</info> application plugin{}".format(
                    len(info["application_plugins"]),
                    "s" if len(info["application_plugins"]) > 1 else "",
                )

            self.line(provide_line)

            if package.requires:
                self.line("")
                self.line("      <info>Dependencies</info>")
                for dependency in package.requires:
                    self.line(
                        "        - {} (<c2>{}</c2>)".format(
                            dependency.pretty_name, dependency.pretty_constraint
                        )
                    )

        return 0
