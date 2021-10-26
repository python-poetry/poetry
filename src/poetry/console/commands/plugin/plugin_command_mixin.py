import os

from typing import TYPE_CHECKING
from typing import List

import tomlkit

from poetry.packages.locker import BaseLocker
from poetry.utils.helpers import canonicalize_name


if TYPE_CHECKING:
    from cleo.io.io import IO
    from entrypoints import EntryPoint

    from poetry.core.packages.project_package import ProjectPackage
    from poetry.utils.env import Env


class PluginCommandMixin:
    def create_env_package(
        self, env: "Env", existing_plugins: dict
    ) -> "ProjectPackage":
        from poetry.core.packages.project_package import ProjectPackage
        from poetry.factory import Factory
        from poetry.repositories.installed_repository import InstalledRepository

        # We retrieve the packages installed in the system environment.
        # We assume that this environment will be a self contained virtual environment
        # built by the official installer or by pipx.
        # If not, it might lead to side effects since other installed packages
        # might not be required by Poetry but still taken into account when resolving dependencies.
        installed_repository = InstalledRepository.load(env, with_dependencies=True)

        root_package = None
        for package in installed_repository.packages:
            if package.name == "poetry":
                root_package = ProjectPackage("-root-", package.version)
                for dependency in package.requires:
                    root_package.add_dependency(dependency)

                root_package.add_dependency(
                    Factory.create_dependency(package.name, package.version.text)
                )

                break

        # Add plugin packages if they do not already exist
        entry_points = set()
        for entry_point in self.get_plugin_entry_points():
            if entry_point.distro.name in entry_points:
                continue

            entry_points.add(entry_point.distro.name)

            found = False
            for dependency in root_package.requires:
                if canonicalize_name(entry_point.distro.name) == dependency.name:
                    found = True

                    break

            if found:
                continue

            version = entry_point.distro.version
            if canonicalize_name(entry_point.distro.name) in existing_plugins:
                version = existing_plugins[canonicalize_name(entry_point.distro.name)]

            root_package.add_dependency(
                Factory.create_dependency(entry_point.distro.name, version)
            )

        root_package.python_versions = ".".join(str(v) for v in env.version_info[:3])

        return root_package

    def get_plugin_entry_points(self) -> List["EntryPoint"]:
        from poetry.plugins.plugin_manager import PluginManager

        return (
            PluginManager("application.plugin").get_plugin_entry_points()
            + PluginManager("plugin").get_plugin_entry_points()
        )

    def update(
        self,
        env: "Env",
        root_package: "ProjectPackage",
        io: "IO",
        whitelist: List[str],
    ) -> int:
        import os

        from pathlib import Path

        from poetry.factory import Factory
        from poetry.installation.installer import Installer
        from poetry.repositories.installed_repository import InstalledRepository

        env_dir = Path(
            os.getenv("POETRY_HOME") if os.getenv("POETRY_HOME") else env.path
        )

        locker = BaseLocker(env_dir, {})

        locker.set_lock_data(root_package, InstalledRepository.load(env).packages)

        config = Factory.create_config()

        installer = Installer(
            io,
            env,
            root_package,
            locker,
            Factory.create_pool(config),
            config,
        )
        installer.update(True)
        installer.whitelist(whitelist)
        installer.dry_run(self.option("dry-run"))
        installer.use_executor(config.get("experimental.new-installer", False))
        installer.requires_synchronization(False)

        return installer.run()
