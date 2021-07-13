from typing import TYPE_CHECKING
from typing import Iterable
from typing import List
from typing import Optional
from typing import Union

from cleo.io.io import IO
from cleo.io.null_io import NullIO

from poetry.config.config import Config
from poetry.core.packages.project_package import ProjectPackage
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


if TYPE_CHECKING:
    from poetry.utils.env import Env

    from .operations import OperationTypes


class Installer:
    def __init__(
        self,
        io: IO,
        env: "Env",
        package: ProjectPackage,
        locker: Locker,
        pool: Pool,
        config: Config,
        installed: Union[Repository, None] = None,
        executor: Optional[Executor] = None,
    ):
        self._io = io
        self._env = env
        self._package = package
        self._locker = locker
        self._pool = pool

        self._dry_run = False
        self._requires_synchronization = False
        self._update = False
        self._verbose = False
        self._write_lock = True
        self._without_groups = None
        self._with_groups = None
        self._only_groups = None

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
    def executor(self) -> Executor:
        return self._executor

    @property
    def installer(self) -> BaseInstaller:
        return self._installer

    def set_package(self, package: ProjectPackage) -> "Installer":
        self._package = package

        return self

    def set_locker(self, locker: Locker) -> "Installer":
        self._locker = locker

        return self

    def run(self) -> int:
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

    def dry_run(self, dry_run: bool = True) -> "Installer":
        self._dry_run = dry_run
        self._executor.dry_run(dry_run)

        return self

    def is_dry_run(self) -> bool:
        return self._dry_run

    def requires_synchronization(
        self, requires_synchronization: bool = True
    ) -> "Installer":
        self._requires_synchronization = requires_synchronization

        return self

    def verbose(self, verbose: bool = True) -> "Installer":
        self._verbose = verbose
        self._executor.verbose(verbose)

        return self

    def is_verbose(self) -> bool:
        return self._verbose

    def without_groups(self, groups: List[str]) -> "Installer":
        self._without_groups = groups

        return self

    def with_groups(self, groups: List[str]) -> "Installer":
        self._with_groups = groups

        return self

    def only_groups(self, groups: List[str]) -> "Installer":
        self._only_groups = groups

        return self

    def update(self, update: bool = True) -> "Installer":
        self._update = update

        return self

    def lock(self, update: bool = True) -> "Installer":
        """
        Prepare the installer for locking only.
        """
        self.update(update=update)
        self.execute_operations(False)
        self._lock = True

        return self

    def is_updating(self) -> bool:
        return self._update

    def execute_operations(self, execute: bool = True) -> "Installer":
        self._execute_operations = execute

        if not execute:
            self._executor.disable()

        return self

    def whitelist(self, packages: Iterable[str]) -> "Installer":
        self._whitelist = [canonicalize_name(p) for p in packages]

        return self

    def extras(self, extras: list) -> "Installer":
        self._extras = extras

        return self

    def use_executor(self, use_executor: bool = True) -> "Installer":
        self._use_executor = use_executor

        return self

    def _do_refresh(self) -> int:
        from poetry.puzzle import Solver

        # Checking extras
        for extra in self._extras:
            if extra not in self._package.extras:
                raise ValueError(f"Extra [{extra}] is not specified.")

        locked_repository = self._locker.locked_repository(True)
        solver = Solver(
            self._package,
            self._pool,
            locked_repository,
            locked_repository,
            self._io,
        )

        ops = solver.solve(use_latest=[]).calculate_operations()

        local_repo = Repository()
        self._populate_local_repo(local_repo, ops)

        self._write_lock_file(local_repo, force=True)

        return 0

    def _do_install(self, local_repo: Repository) -> int:
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
                    raise ValueError(f"Extra [{extra}] is not specified.")

            self._io.write_line("<info>Updating dependencies</>")
            solver = Solver(
                self._package,
                self._pool,
                self._installed_repository,
                locked_repository,
                self._io,
            )

            ops = solver.solve(use_latest=self._whitelist).calculate_operations()
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
                    raise ValueError(f"Extra [{extra}] is not specified.")

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

        if self._without_groups or self._with_groups or self._only_groups:
            if self._with_groups:
                # Default dependencies and opted-in optional dependencies
                root = self._package.with_dependency_groups(self._with_groups)
            elif self._without_groups:
                # Default dependencies without selected groups
                root = self._package.without_dependency_groups(self._without_groups)
            else:
                # Only selected groups
                root = self._package.with_dependency_groups(
                    self._only_groups, only=True
                )
        else:
            root = self._package.without_optional_dependency_groups()

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

        solver = Solver(
            root, pool, self._installed_repository, locked_repository, NullIO()
        )
        # Everything is resolved at this point, so we no longer need
        # to load deferred dependencies (i.e. VCS, URL and path dependencies)
        solver.provider.load_deferred(False)

        with solver.use_environment(self._env):
            ops = solver.solve(use_latest=self._whitelist).calculate_operations(
                with_uninstalls=self._requires_synchronization,
                synchronize=self._requires_synchronization,
            )

        if not self._requires_synchronization:
            # If no packages synchronisation has been requested we need
            # to calculate the uninstall operations
            from poetry.puzzle.transaction import Transaction

            transaction = Transaction(
                locked_repository.packages,
                [(package, 0) for package in local_repo.packages],
                installed_packages=self._installed_repository.packages,
                root_package=root,
            )

            ops = [
                op
                for op in transaction.calculate_operations(with_uninstalls=True)
                if op.job_type == "uninstall"
            ] + ops

        # We need to filter operations so that packages
        # not compatible with the current system,
        # or optional and not requested, are dropped
        self._filter_operations(ops, local_repo)

        # Execute operations
        return self._execute(ops)

    def _write_lock_file(self, repo: Repository, force: bool = True) -> None:
        if force or (self._update and self._write_lock):
            updated_lock = self._locker.set_lock_data(self._package, repo.packages)

            if updated_lock:
                self._io.write_line("")
                self._io.write_line("<info>Writing lock file</>")

    def _execute(self, operations: List["OperationTypes"]) -> int:
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
                    f", <info>{skipped}</> skipped"
                    if skipped and self.is_verbose()
                    else "",
                )
            )

        self._io.write_line("")

        for op in operations:
            self._execute_operation(op)

        return 0

    def _execute_operation(self, operation: Operation) -> None:
        """
        Execute a given operation.
        """
        method = operation.job_type

        getattr(self, f"_execute_{method}")(operation)

    def _execute_install(self, operation: Install) -> None:
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

    def _execute_update(self, operation: Update) -> None:
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

    def _execute_uninstall(self, operation: Uninstall) -> None:
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

    def _populate_local_repo(
        self, local_repo: Repository, ops: List[Operation]
    ) -> None:
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
        self, locked_repository: Repository
    ) -> List[Operation]:
        installed_repo = self._installed_repository
        ops = []

        extra_packages = self._get_extra_packages(locked_repository)
        for locked in locked_repository.packages:
            is_installed = False
            for installed in installed_repo.packages:
                if locked.name == installed.name:
                    is_installed = True
                    if locked.optional and locked.name not in extra_packages:
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

    def _filter_operations(self, ops: List[Operation], repo: Repository) -> None:
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

    def _get_extra_packages(self, repo: Repository) -> List[str]:
        """
        Returns all package names required by extras.

        Maybe we just let the solver handle it?
        """
        if self._update:
            extras = {k: [d.name for d in v] for k, v in self._package.extras.items()}
        else:
            extras = self._locker.lock_data.get("extras", {})

        return list(get_extra_package_names(repo.packages, extras, self._extras))

    def _get_installer(self) -> BaseInstaller:
        return PipInstaller(self._env, self._io, self._pool)

    def _get_installed(self) -> InstalledRepository:
        return InstalledRepository.load(self._env)
