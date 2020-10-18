from typing import List
from typing import Optional
from typing import Union

from clikit.api.io import IO

from poetry.config.config import Config
from poetry.core.packages.project_package import ProjectPackage
from poetry.io.null_io import NullIO
from poetry.packages import Locker
from poetry.repositories import Pool
from poetry.repositories import Repository
from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils.extras import get_extra_package_names
from poetry.utils.helpers import canonicalize_name

from .base_installer import BaseInstaller
from .executor import Executor
from .operations import Install
from .operations import Uninstall
from .operations import Update
from .operations.operation import Operation
from .pip_installer import PipInstaller


class Installer:
    def __init__(
        self,
        io,  # type: IO
        env,
        package,  # type: ProjectPackage
        locker,  # type: Locker
        pool,  # type: Pool
        config,  # type: Config
        installed=None,  # type: Union[InstalledRepository, None]
        executor=None,  # type: Optional[Executor]
    ):
        self._io = io
        self._env = env
        self._package = package
        self._locker = locker
        self._pool = pool

        self._dry_run = False
        self._remove_untracked = False
        self._update = False
        self._verbose = False
        self._write_lock = True
        self._dev_mode = True
        self._execute_operations = True
        self._lock = False

        self._whitelist = []

        self._extras = []

        if executor is None:
            executor = Executor(self._env, self._pool, config, self._io)

        self._executor = executor
        self._use_executor = False

        self._installer = self._get_installer()
        if installed is None:
            installed = self._get_installed()

        self._installed_repository = installed

    @property
    def executor(self):
        return self._executor

    @property
    def installer(self):
        return self._installer

    def set_package(self, package):  # type: (ProjectPackage) -> Installer
        self._package = package

        return self

    def set_locker(self, locker):  # type: (Locker) -> Installer
        self._locker = locker

        return self

    def run(self):
        # Check if refresh
        if not self._update and self._lock and self._locker.is_locked():
            return self._do_refresh()

        # Force update if there is no lock file present
        if not self._update and not self._locker.is_locked():
            self._update = True

        if self.is_dry_run():
            self.verbose(True)
            self._write_lock = False
            self._execute_operations = False

        local_repo = Repository()

        return self._do_install(local_repo)

    def dry_run(self, dry_run=True):  # type: (bool) -> Installer
        self._dry_run = dry_run
        self._executor.dry_run(dry_run)

        return self

    def is_dry_run(self):  # type: () -> bool
        return self._dry_run

    def remove_untracked(self, remove_untracked=True):  # type: (bool) -> Installer
        self._remove_untracked = remove_untracked

        return self

    def is_remove_untracked(self):  # type: () -> bool
        return self._remove_untracked

    def verbose(self, verbose=True):  # type: (bool) -> Installer
        self._verbose = verbose
        self._executor.verbose(verbose)

        return self

    def is_verbose(self):  # type: () -> bool
        return self._verbose

    def dev_mode(self, dev_mode=True):  # type: (bool) -> Installer
        self._dev_mode = dev_mode

        return self

    def is_dev_mode(self):  # type: () -> bool
        return self._dev_mode

    def update(self, update=True):  # type: (bool) -> Installer
        self._update = update

        return self

    def lock(self, update=True):  # type: (bool) -> Installer
        """
        Prepare the installer for locking only.
        """
        self.update(update=update)
        self.execute_operations(False)
        self._lock = True

        return self

    def is_updating(self):  # type: () -> bool
        return self._update

    def execute_operations(self, execute=True):  # type: (bool) -> Installer
        self._execute_operations = execute

        if not execute:
            self._executor.disable()

        return self

    def whitelist(self, packages):  # type: (dict) -> Installer
        self._whitelist = [canonicalize_name(p) for p in packages]

        return self

    def extras(self, extras):  # type: (list) -> Installer
        self._extras = extras

        return self

    def use_executor(self, use_executor=True):  # type: (bool) -> Installer
        self._use_executor = use_executor

        return self

    def _do_refresh(self):
        from poetry.puzzle import Solver

        # Checking extras
        for extra in self._extras:
            if extra not in self._package.extras:
                raise ValueError("Extra [{}] is not specified.".format(extra))

        locked_repository = self._locker.locked_repository(True)
        solver = Solver(
            self._package,
            self._pool,
            locked_repository,
            locked_repository,
            self._io,  # noqa
        )

        ops = solver.solve(use_latest=[])

        local_repo = Repository()
        self._populate_local_repo(local_repo, ops)

        self._write_lock_file(local_repo, force=True)

        return 0

    def _do_install(self, local_repo):
        from poetry.puzzle import Solver

        locked_repository = Repository()
        if self._update:
            if self._locker.is_locked() and not self._lock:
                locked_repository = self._locker.locked_repository(True)

                # If no packages have been whitelisted (The ones we want to update),
                # we whitelist every package in the lock file.
                if not self._whitelist:
                    for pkg in locked_repository.packages:
                        self._whitelist.append(pkg.name)

            # Checking extras
            for extra in self._extras:
                if extra not in self._package.extras:
                    raise ValueError("Extra [{}] is not specified.".format(extra))

            self._io.write_line("<info>Updating dependencies</>")
            solver = Solver(
                self._package,
                self._pool,
                self._installed_repository,
                locked_repository,
                self._io,
                remove_untracked=self._remove_untracked,
            )

            ops = solver.solve(use_latest=self._whitelist)
        else:
            self._io.write_line("<info>Installing dependencies from lock file</>")

            locked_repository = self._locker.locked_repository(True)

            if not self._locker.is_fresh():
                self._io.write_line(
                    "<warning>"
                    "Warning: The lock file is not up to date with "
                    "the latest changes in pyproject.toml. "
                    "You may be getting outdated dependencies. "
                    "Run update to update them."
                    "</warning>"
                )

            for extra in self._extras:
                if extra not in self._locker.lock_data.get("extras", {}):
                    raise ValueError("Extra [{}] is not specified.".format(extra))

            # If we are installing from lock
            # Filter the operations by comparing it with what is
            # currently installed
            ops = self._get_operations_from_lock(locked_repository)

        self._populate_local_repo(local_repo, ops)

        if self._update:
            self._write_lock_file(local_repo)

            if self._lock:
                # If we are only in lock mode, no need to go any further
                return 0

        root = self._package
        if not self.is_dev_mode():
            root = root.clone()
            del root.dev_requires[:]

        if self._io.is_verbose():
            self._io.write_line("")
            self._io.write_line(
                "<info>Finding the necessary packages for the current system</>"
            )

        # We resolve again by only using the lock file
        pool = Pool(ignore_repository_names=True)

        # Making a new repo containing the packages
        # newly resolved and the ones from the current lock file
        repo = Repository()
        for package in local_repo.packages + locked_repository.packages:
            if not repo.has_package(package):
                repo.add_package(package)

        pool.add_repository(repo)

        # We whitelist all packages to be sure
        # that the latest ones are picked up
        whitelist = []
        for pkg in locked_repository.packages:
            whitelist.append(pkg.name)

        solver = Solver(
            root,
            pool,
            self._installed_repository,
            locked_repository,
            NullIO(),
            remove_untracked=self._remove_untracked,
        )

        with solver.use_environment(self._env):
            ops = solver.solve(use_latest=whitelist)

        # We need to filter operations so that packages
        # not compatible with the current system,
        # or optional and not requested, are dropped
        self._filter_operations(ops, local_repo)

        # Execute operations
        return self._execute(ops)

    def _write_lock_file(self, repo, force=True):  # type: (Repository, bool) -> None
        if force or (self._update and self._write_lock):
            updated_lock = self._locker.set_lock_data(self._package, repo.packages)

            if updated_lock:
                self._io.write_line("")
                self._io.write_line("<info>Writing lock file</>")

    def _execute(self, operations):
        if self._use_executor:
            return self._executor.execute(operations)

        if not operations and (self._execute_operations or self._dry_run):
            self._io.write_line("No dependencies to install or update")

        if operations and (self._execute_operations or self._dry_run):
            installs = 0
            updates = 0
            uninstalls = 0
            skipped = 0
            for op in operations:
                if op.skipped:
                    skipped += 1
                elif op.job_type == "install":
                    installs += 1
                elif op.job_type == "update":
                    updates += 1
                elif op.job_type == "uninstall":
                    uninstalls += 1

            self._io.write_line("")
            self._io.write_line(
                "Package operations: "
                "<info>{}</> install{}, "
                "<info>{}</> update{}, "
                "<info>{}</> removal{}"
                "{}".format(
                    installs,
                    "" if installs == 1 else "s",
                    updates,
                    "" if updates == 1 else "s",
                    uninstalls,
                    "" if uninstalls == 1 else "s",
                    ", <info>{}</> skipped".format(skipped)
                    if skipped and self.is_verbose()
                    else "",
                )
            )

        self._io.write_line("")

        for op in operations:
            self._execute_operation(op)

        return 0

    def _execute_operation(self, operation):  # type: (Operation) -> None
        """
        Execute a given operation.
        """
        method = operation.job_type

        getattr(self, "_execute_{}".format(method))(operation)

    def _execute_install(self, operation):  # type: (Install) -> None
        if operation.skipped:
            if self.is_verbose() and (self._execute_operations or self.is_dry_run()):
                self._io.write_line(
                    "  - Skipping <c1>{}</c1> (<c2>{}</c2>) {}".format(
                        operation.package.pretty_name,
                        operation.package.full_pretty_version,
                        operation.skip_reason,
                    )
                )

            return

        if self._execute_operations or self.is_dry_run():
            self._io.write_line(
                "  - Installing <c1>{}</c1> (<c2>{}</c2>)".format(
                    operation.package.pretty_name, operation.package.full_pretty_version
                )
            )

        if not self._execute_operations:
            return

        self._installer.install(operation.package)

    def _execute_update(self, operation):  # type: (Update) -> None
        source = operation.initial_package
        target = operation.target_package

        if operation.skipped:
            if self.is_verbose() and (self._execute_operations or self.is_dry_run()):
                self._io.write_line(
                    "  - Skipping <c1>{}</c1> (<c2>{}</c2>) {}".format(
                        target.pretty_name,
                        target.full_pretty_version,
                        operation.skip_reason,
                    )
                )

            return

        if self._execute_operations or self.is_dry_run():
            self._io.write_line(
                "  - Updating <c1>{}</c1> (<c2>{}</c2> -> <c2>{}</c2>)".format(
                    target.pretty_name,
                    source.full_pretty_version,
                    target.full_pretty_version,
                )
            )

        if not self._execute_operations:
            return

        self._installer.update(source, target)

    def _execute_uninstall(self, operation):  # type: (Uninstall) -> None
        if operation.skipped:
            if self.is_verbose() and (self._execute_operations or self.is_dry_run()):
                self._io.write_line(
                    "  - Not removing <c1>{}</c1> (<c2>{}</c2>) {}".format(
                        operation.package.pretty_name,
                        operation.package.full_pretty_version,
                        operation.skip_reason,
                    )
                )

            return

        if self._execute_operations or self.is_dry_run():
            self._io.write_line(
                "  - Removing <c1>{}</c1> (<c2>{}</c2>)".format(
                    operation.package.pretty_name, operation.package.full_pretty_version
                )
            )

        if not self._execute_operations:
            return

        self._installer.remove(operation.package)

    def _populate_local_repo(self, local_repo, ops):
        for op in ops:
            if isinstance(op, Uninstall):
                continue
            elif isinstance(op, Update):
                package = op.target_package
            else:
                package = op.package

            if not local_repo.has_package(package):
                local_repo.add_package(package)

    def _get_operations_from_lock(
        self, locked_repository  # type: Repository
    ):  # type: (...) -> List[Operation]
        installed_repo = self._installed_repository
        ops = []

        extra_packages = self._get_extra_packages(locked_repository)
        for locked in locked_repository.packages:
            is_installed = False
            for installed in installed_repo.packages:
                if locked.name == installed.name:
                    is_installed = True
                    if locked.category == "dev" and not self.is_dev_mode():
                        ops.append(Uninstall(locked))
                    elif locked.optional and locked.name not in extra_packages:
                        # Installed but optional and not requested in extras
                        ops.append(Uninstall(locked))
                    elif locked.version != installed.version:
                        ops.append(Update(installed, locked))

            # If it's optional and not in required extras
            # we do not install
            if locked.optional and locked.name not in extra_packages:
                continue

            op = Install(locked)
            if is_installed:
                op.skip("Already installed")

            ops.append(op)

        return ops

    def _filter_operations(
        self, ops, repo
    ):  # type: (List[Operation], Repository) -> None
        extra_packages = self._get_extra_packages(repo)
        for op in ops:
            if isinstance(op, Update):
                package = op.target_package
            else:
                package = op.package

            if op.job_type == "uninstall":
                continue

            if not self._env.is_valid_for_marker(package.marker):
                op.skip("Not needed for the current environment")
                continue

            if self._update:
                extras = {}
                for extra, deps in self._package.extras.items():
                    extras[extra] = [dep.name for dep in deps]
            else:
                extras = {}
                for extra, deps in self._locker.lock_data.get("extras", {}).items():
                    extras[extra] = [dep.lower() for dep in deps]

            # If a package is optional and not requested
            # in any extra we skip it
            if package.optional:
                if package.name not in extra_packages:
                    op.skip("Not required")

            # If the package is a dev package and dev packages
            # are not requested, we skip it
            if package.category == "dev" and not self.is_dev_mode():
                op.skip("Dev dependencies not requested")

    def _get_extra_packages(self, repo):  # type: (Repository) -> List[str]
        """
        Returns all package names required by extras.

        Maybe we just let the solver handle it?
        """
        if self._update:
            extras = {k: [d.name for d in v] for k, v in self._package.extras.items()}
        else:
            extras = self._locker.lock_data.get("extras", {})

        return list(get_extra_package_names(repo.packages, extras, self._extras))

    def _get_installer(self):  # type: () -> BaseInstaller
        return PipInstaller(self._env, self._io, self._pool)

    def _get_installed(self):  # type: () -> InstalledRepository
        return InstalledRepository.load(self._env)
