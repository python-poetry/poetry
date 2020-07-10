import os

from typing import TYPE_CHECKING
from typing import Optional
from typing import Tuple

from cleo import argument

from ..init import InitCommand


if TYPE_CHECKING:
    from poetry.utils._compat import Path
    from poetry.utils.env import Env


class PluginInstallCommand(InitCommand):

    name = "install"

    description = "Install a new plugin."

    arguments = [
        argument("plugins", "The names of the plugins to install.", multiple=True)
    ]

    @property
    def home(self):
        from poetry.utils._compat import Path

        return Path(os.environ.get("POETRY_HOME", "~/.poetry")).expanduser()

    @property
    def bin(self):
        return self.home / "bin"

    @property
    def lib(self):
        return self.home / "lib"

    @property
    def plugins(self):
        return self.home / "plugins"

    def handle(self):  # type: () -> Optional[int]
        from poetry.core.semver import parse_constraint
        from poetry.puzzle.solver import Solver
        from poetry.repositories.pool import Pool
        from poetry.repositories.pool import Repository
        from poetry.utils.env import EnvManager

        plugins = self.argument("plugins")
        plugins = self._determine_requirements(plugins)

        system_env = EnvManager.get_system_env()
        package, installed_repository = self.get_elements_for_env(system_env)

        dependencies = []
        for _constraint in plugins:
            if "version" in _constraint:
                # Validate version constraint
                parse_constraint(_constraint["version"])

            constraint = {}
            for name, value in _constraint.items():
                if name == "name":
                    continue

                constraint[name] = value

            if len(constraint) == 1 and "version" in constraint:
                constraint = constraint["version"]

            dependencies.append((_constraint["name"], constraint))

        pool = Pool()
        pool.add_repository(installed_repository)

        locked = Repository()

        solver = Solver(package, pool, installed_repository, locked, self._io)
        with solver.use_environment(system_env):
            for op in solver.solve():
                if op.job_type != "install":
                    continue

                locked.add_package(op.package)

        for name, constraint in dependencies:
            package.add_dependency(name, constraint)

        solver = Solver(package, pool, installed_repository, locked, self._io)
        with solver.use_environment(system_env):
            for op in solver.solve():
                if op.skipped:
                    continue

                print(op)

    def get_elements_for_env(
        self, env
    ):  # type: () -> Tuple[Package, InstalledRepository]
        from poetry.__version__ import __version__
        from poetry.core.packages.package import Package
        from poetry.repositories.installed_repository import InstalledRepository
        from poetry.utils.env import EnvManager

        env = EnvManager.get_system_env()

        poetry_package = None
        if not self.is_installed_with_installer():
            installed_repository = InstalledRepository.load(env, with_dependencies=True)
            # Finding the poetry package
            for package in installed_repository.packages:
                if package.name == "poetry":
                    poetry_package = package
                    continue
        else:
            poetry_package = Package("poetry", __version__)
            env._sys_path = [str(self.get_vendor_directory_for_env(env))]

            for package in InstalledRepository.load(env).packages:
                poetry_package.requires.append(package.to_dependency())

            env._sys_path.insert(0, str(self.plugins))
            installed_repository = InstalledRepository.load(env, with_dependencies=True)
            installed_repository.add_package(poetry_package)

        return poetry_package, installed_repository

    def get_vendor_directory_for_env(self, env):  # type: (Env) -> Path
        return (
            self.lib
            / "poetry"
            / "_vendor"
            / "py{}".format(".".join(str(v) for v in env.version_info[:2]))
        )

    def is_installed_with_installer(self):  # type: () -> bool
        from poetry.utils._compat import Path

        current = Path(__file__)
        try:
            current.relative_to(self.home)
        except ValueError:
            return False

        return True

    def _install_for_installer(self, plugin):  # type: () -> bool
        from poetry.factory import Factory
        from poetry.installation.installer import Installer
        from poetry.io.null_io import NullIO
        from poetry.packages.locker import NullLocker
        from poetry.repositories.installed_repository import InstalledRepository
        from poetry.repositories.pool import Pool
        from poetry.repositories.pypi_repository import PyPiRepository
        from poetry.utils._compat import Path
        from poetry.utils.env import EnvManager

        env = EnvManager.get_system_env()
        installed_repository = InstalledRepository.load(env)
        poetry_package = None
        plugin_package = None
        for package in installed_repository.packages:
            if package.name == "poetry":
                poetry_package = package

            if package.name == plugin:
                plugin_package = package

        if plugin_package is not None:
            raise RuntimeError('The plugin "{}" is already installed'.format(plugin))

        if poetry_package.source_type == "directory":
            from poetry.puzzle.provider import Provider

            poetry_package = Provider.get_package_from_directory(
                Path(poetry_package.source_url), "poetry"
            )

        pool = Pool()
        pool.add_repository(installed_repository, default=True)
        pool.add_repository(PyPiRepository())

        installer = Installer(
            NullIO(),
            env,
            poetry_package,
            NullLocker(),
            pool,
            Factory.create_config(NullIO()),
        )
        installer.use_executor()
        installer.whitelist([plugin])
        installer.dry_run()
        installer.run()
