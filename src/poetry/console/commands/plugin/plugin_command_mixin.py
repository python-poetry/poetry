from typing import TYPE_CHECKING
from typing import List


if TYPE_CHECKING:
    from cleo.io.io import IO
    from entrypoints import EntryPoint

    from poetry.core.packages.project_package import ProjectPackage
    from poetry.utils.env import Env


class PluginCommandMixin:
    def create_env_package(self, env: "Env") -> "ProjectPackage":
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
            print(package)
            if package.name == "poetry":
                root_package = ProjectPackage("-root-", package.version)
                for dependency in package.requires:
                    root_package.add_dependency(dependency)

                root_package.add_dependency(
                    Factory.create_dependency(package.name, package.version.text)
                )

                break

        root_package.python_versions = ".".join(str(v) for v in env.version_info[:3])

        return root_package

    def get_plugin_entry_points(self) -> List["EntryPoint"]:
        from poetry.plugins.plugin_manager import PluginManager

        return (
            PluginManager("application.plugin").get_plugin_entry_points()
            + PluginManager("plugin").get_plugin_entry_points()
        )

    def update(self, env: "Env", root_package: "ProjectPackage", io: "IO") -> int:
        import os

        from pathlib import Path

        from poetry.factory import Factory
        from poetry.installation.installer import Installer

        env_dir = Path(
            os.getenv("POETRY_HOME") if os.getenv("POETRY_HOME") else env.path
        )
        poetry = Factory().create_poetry(env_dir)
        poetry._package = root_package

        installer = Installer(
            io,
            env,
            poetry.package,
            poetry.locker,
            poetry.pool,
            poetry.config,
        )
        installer.dry_run(self.option("dry-run"))
        installer.use_executor(poetry.config.get("experimental.new-installer", False))

        return installer.run()
