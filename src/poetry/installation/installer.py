from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from cleo.io.null_io import NullIO
from packaging.utils import canonicalize_name

from poetry.installation.executor import Executor
from poetry.installation.operations import Uninstall
from poetry.installation.operations import Update
from poetry.repositories import Repository
from poetry.repositories import RepositoryPool
from poetry.repositories.installed_repository import InstalledRepository
from poetry.repositories.lockfile_repository import LockfileRepository


if TYPE_CHECKING:
    from collections.abc import Iterable

    from cleo.io.io import IO
    from packaging.utils import NormalizedName
    from poetry.core.packages.path_dependency import PathDependency
    from poetry.core.packages.project_package import ProjectPackage

    from poetry.config.config import Config
    from poetry.installation.operations.operation import Operation
    from poetry.packages import Locker
    from poetry.utils.env import Env


class Installer:
    def __init__(
        self,
        io: IO,
        env: Env,
        package: ProjectPackage,
        locker: Locker,
        pool: RepositoryPool,
        config: Config,
        installed: Repository | None = None,
        executor: Executor | None = None,
        disable_cache: bool = False,
    ) -> None:
        self._io = io
        self._env = env
        self._package = package
        self._locker = locker
        self._pool = pool
        self._config = config

        self._dry_run = False
        self._requires_synchronization = False
        self._update = False
        self._verbose = False
        self._groups: Iterable[str] | None = None
        self._skip_directory = False
        self._lock = False

        self._whitelist: list[NormalizedName] = []

        self._extras: list[NormalizedName] = []

        if executor is None:
            executor = Executor(
                self._env, self._pool, config, self._io, disable_cache=disable_cache
            )

        self._executor = executor

        if installed is None:
            installed = self._get_installed()

        self._installed_repository = installed

    @property
    def executor(self) -> Executor:
        return self._executor

    def set_package(self, package: ProjectPackage) -> Installer:
        self._package = package

        return self

    def set_locker(self, locker: Locker) -> Installer:
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

        return self._do_install()

    def dry_run(self, dry_run: bool = True) -> Installer:
        self._dry_run = dry_run
        self._executor.dry_run(dry_run)

        return self

    def is_dry_run(self) -> bool:
        return self._dry_run

    def requires_synchronization(
        self, requires_synchronization: bool = True
    ) -> Installer:
        self._requires_synchronization = requires_synchronization

        return self

    def verbose(self, verbose: bool = True) -> Installer:
        self._verbose = verbose
        self._executor.verbose(verbose)

        return self

    def is_verbose(self) -> bool:
        return self._verbose

    def only_groups(self, groups: Iterable[str]) -> Installer:
        self._groups = groups

        return self

    def update(self, update: bool = True) -> Installer:
        self._update = update

        return self

    def skip_directory(self, skip_directory: bool = False) -> Installer:
        self._skip_directory = skip_directory

        return self

    def lock(self, update: bool = True) -> Installer:
        """
        Prepare the installer for locking only.
        """
        self.update(update=update)
        self.execute_operations(False)
        self._lock = True

        return self

    def is_updating(self) -> bool:
        return self._update

    def execute_operations(self, execute: bool = True) -> Installer:
        if not execute:
            self._executor.disable()

        return self

    def whitelist(self, packages: Iterable[str]) -> Installer:
        self._whitelist = [canonicalize_name(p) for p in packages]

        return self

    def extras(self, extras: list[str]) -> Installer:
        self._extras = [canonicalize_name(extra) for extra in extras]

        return self

    def _do_refresh(self) -> int:
        from poetry.puzzle.solver import Solver

        # Checking extras
        for extra in self._extras:
            if extra not in self._package.extras:
                raise ValueError(f"Extra [{extra}] is not specified.")

        locked_repository = self._locker.locked_repository()
        solver = Solver(
            self._package,
            self._pool,
            locked_repository.packages,
            locked_repository.packages,
            self._io,
        )

        # Always re-solve directory dependencies, otherwise we can't determine
        # if anything has changed (and the lock file contains an invalid version).
        use_latest = [
            p.name for p in locked_repository.packages if p.source_type == "directory"
        ]

        with solver.provider.use_source_root(
            source_root=self._env.path.joinpath("src")
        ):
            ops = solver.solve(use_latest=use_latest).calculate_operations()

        lockfile_repo = LockfileRepository()
        self._populate_lockfile_repo(lockfile_repo, ops)

        self._write_lock_file(lockfile_repo, force=True)

        return 0

    def _do_install(self) -> int:
        from poetry.puzzle.solver import Solver

        locked_repository = Repository("poetry-locked")
        if self._update:
            if not self._lock and self._locker.is_locked():
                locked_repository = self._locker.locked_repository()

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
                self._installed_repository.packages,
                locked_repository.packages,
                self._io,
            )

            with solver.provider.use_source_root(
                source_root=self._env.path.joinpath("src")
            ):
                ops = solver.solve(use_latest=self._whitelist).calculate_operations()

            lockfile_repo = LockfileRepository()
            self._populate_lockfile_repo(lockfile_repo, ops)

        else:
            self._io.write_line("<info>Installing dependencies from lock file</>")

            if not self._locker.is_fresh():
                raise ValueError(
                    "pyproject.toml changed significantly since poetry.lock was last"
                    " generated. Run `poetry lock [--no-update]` to fix the lock file."
                )

            locker_extras = {
                canonicalize_name(extra)
                for extra in self._locker.lock_data.get("extras", {})
            }
            for extra in self._extras:
                if extra not in locker_extras:
                    raise ValueError(f"Extra [{extra}] is not specified.")

            locked_repository = self._locker.locked_repository()
            lockfile_repo = locked_repository

        if not self.executor.enabled:
            # If we are only in lock mode, no need to go any further
            self._write_lock_file(lockfile_repo)
            return 0

        if self._io.is_verbose():
            self._io.write_line("")
            self._io.write_line(
                "<info>Finding the necessary packages for the current system</>"
            )

        if self._groups is not None:
            root = self._package.with_dependency_groups(list(self._groups), only=True)
        else:
            root = self._package.without_optional_dependency_groups()

        # We resolve again by only using the lock file
        packages = lockfile_repo.packages + locked_repository.packages
        pool = RepositoryPool.from_packages(packages, self._config)

        solver = Solver(
            root,
            pool,
            self._installed_repository.packages,
            locked_repository.packages,
            NullIO(),
        )
        # Everything is resolved at this point, so we no longer need
        # to load deferred dependencies (i.e. VCS, URL and path dependencies)
        solver.provider.load_deferred(False)

        with solver.use_environment(self._env):
            ops = solver.solve(use_latest=self._whitelist).calculate_operations(
                with_uninstalls=self._requires_synchronization or self._update,
                synchronize=self._requires_synchronization,
                skip_directory=self._skip_directory,
                extras=set(self._extras),
            )

        # Validate the dependencies
        for op in ops:
            dep = op.package.to_dependency()
            if dep.is_file() or dep.is_directory():
                dep = cast("PathDependency", dep)
                dep.validate(raise_error=not op.skipped)

        # Execute operations
        status = self._execute(ops)

        if status == 0 and self._update:
            # Only write lock file when installation is success
            self._write_lock_file(lockfile_repo)

        return status

    def _write_lock_file(self, repo: LockfileRepository, force: bool = False) -> None:
        if not self.is_dry_run() and (force or self._update):
            updated_lock = self._locker.set_lock_data(self._package, repo.packages)

            if updated_lock:
                self._io.write_line("")
                self._io.write_line("<info>Lock file written</>")

    def _execute(self, operations: list[Operation]) -> int:
        return self._executor.execute(operations)

    def _populate_lockfile_repo(
        self, repo: LockfileRepository, ops: Iterable[Operation]
    ) -> None:
        for op in ops:
            if isinstance(op, Uninstall):
                continue

            package = op.target_package if isinstance(op, Update) else op.package
            if not repo.has_package(package):
                repo.add_package(package)

    def _get_installed(self) -> InstalledRepository:
        return InstalledRepository.load(self._env)
