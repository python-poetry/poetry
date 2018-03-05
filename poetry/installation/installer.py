from typing import List

from poetry.packages import Dependency
from poetry.packages import Locker
from poetry.packages import Package
from poetry.puzzle import Solver
from poetry.puzzle.operations import Install
from poetry.puzzle.operations import Uninstall
from poetry.puzzle.operations import Update
from poetry.puzzle.operations.operation import Operation
from poetry.repositories import Pool
from poetry.repositories import Repository
from poetry.repositories.installed_repository import InstalledRepository

from .base_installer import BaseInstaller
from .pip_installer import PipInstaller


class Installer:

    def __init__(self,
                 io,
                 package: Package,
                 locker: Locker,
                 pool: Pool):
        self._io = io
        self._package = package
        self._locker = locker
        self._pool = pool

        self._dry_run = False
        self._update = False
        self._verbose = False
        self._write_lock = True
        self._dev_mode = True
        self._execute_operations = True

        self._whitelist = {}

        self._installer = self._get_installer()

    def run(self):
        # Force update if there is no lock file present
        if not self._update and not self._locker.is_locked():
            self._update = True

        if self.is_dry_run():
            self.verbose(True)
            self._write_lock = False
            self._execute_operations = False

        local_repo = Repository()
        self._do_install(local_repo)

        return 0

    def dry_run(self, dry_run=True) -> 'Installer':
        self._dry_run = dry_run

        return self

    def is_dry_run(self) -> bool:
        return self._dry_run

    def verbose(self, verbose=True) -> 'Installer':
        self._verbose = verbose

        return self

    def is_verbose(self) -> bool:
        return self._verbose

    def dev_mode(self, dev_mode=True) -> 'Installer':
        self._dev_mode = dev_mode

        return self

    def is_dev_mode(self) -> bool:
        return self._dev_mode

    def update(self, update=True) -> 'Installer':
        self._update = update

        return self

    def is_updating(self) -> bool:
        return self._update

    def execute_operations(self, execute=True) -> 'Installer':
        self._execute_operations = execute

        return self

    def whitelist(self, packages: dict) -> 'Installer':
        self._whitelist = packages

        return self

    def _do_install(self, local_repo):
        locked_repository = Repository()
        # initialize locked repo if we are installing from lock
        if not self._update or self._locker.is_locked():
            locked_repository = self._locker.locked_repository(True)

        if self._update:
            self._io.writeln('<info>Updating dependencies</>')
            fixed = []

            # If the whitelist is enabled, packages not in it are fixed
            # to the version specified in the lock
            if self._whitelist:
                # collect packages to fixate from root requirements
                candidates = []
                for package in locked_repository.packages:
                    candidates.append(package)

                # fix them to the version in lock if they are not updateable
                for candidate in candidates:
                    to_fix = True
                    for require in self._whitelist.keys():
                        if require == candidate.name:
                            to_fix = False

                    if to_fix:
                        fixed.append(
                            Dependency(candidate.name, candidate.version)
                        )

            solver = Solver(
                self._package,
                self._pool,
                locked_repository,
                self._io
            )

            request = self._package.requires
            request += self._package.dev_requires

            ops = solver.solve(request, fixed=fixed)
        else:
            self._io.writeln('<info>Installing dependencies from lock file</>')
            if not self._locker.is_fresh():
                self._io.writeln(
                    '<warning>'
                    'Warning: The lock file is not up to date with '
                    'the latest changes in pyproject.toml. '
                    'You may be getting outdated dependencies. '
                    'Run update to update them.'
                    '</warning>'
                )

            # If we are installing from lock
            # Filter the operations by comparing it with what is
            # currently installed
            ops = self._get_operations_from_lock(locked_repository)

        self._populate_local_repo(local_repo, ops, locked_repository)

        self._io.new_line()

        # Execute operations
        if not ops and (self._execute_operations or self._dry_run):
            self._io.writeln('Nothing to install or update')

        if ops and (self._execute_operations or self._dry_run):
            installs = []
            updates = []
            uninstalls = []
            for op in ops:
                if op.job_type == 'install':
                    installs.append(
                        f'{op.package.pretty_name}'
                        f':{op.package.full_pretty_version}'
                    )
                elif op.job_type == 'update':
                    updates.append(
                        f'{op.target_package.pretty_name}'
                        f':{op.target_package.full_pretty_version}'
                    )
                elif op.job_type == 'uninstall':
                    uninstalls.append(
                        f'{op.package.pretty_name}'
                    )

            self._io.new_line()
            self._io.writeln(
                'Package operations: '
                f'<info>{len(installs)}</> install{"" if len(installs) == 1 else "s"}, '
                f'<info>{len(updates)}</> update{"" if len(updates) == 1 else "s"}, '
                f'<info>{len(uninstalls)}</> removal{"" if len(uninstalls) == 1 else "s"}'
                f''
            )
            self._io.new_line()

        # Writing lock before installing
        if self._update and self._write_lock:
            updated_lock = self._locker.set_lock_data(
                self._package,
                local_repo.packages
            )

            if updated_lock:
                self._io.writeln('<info>Writing lock file</>')
                self._io.writeln('')

        for op in ops:
            self._execute(op)

    def _execute(self, operation: Operation) -> None:
        """
        Execute a given operation.
        """
        method = operation.job_type

        getattr(self, f'_execute_{method}')(operation)

    def _execute_install(self, operation: Install) -> None:
        if self._execute_operations or self.is_dry_run():
            self._io.writeln(
                f'  - Installing <info>{operation.package.name}</> '
                f'(<comment>{operation.package.full_pretty_version}</>)'
            )

        if not self._execute_operations:
            return

        self._installer.install(operation.package)

    def _execute_update(self, operation: Update) -> None:
        source = operation.initial_package
        target = operation.target_package

        if self._execute_operations or self.is_dry_run():
            self._io.writeln(
                f'  - Updating <info>{target.name}</> '
                f'(<comment>{source.pretty_version}</>'
                f' -> <comment>{target.pretty_version}</>)'
            )

        if not self._execute_operations:
            return

        self._installer.update(source, target)

    def _execute_uninstall(self, operation: Uninstall) -> None:
        if self._execute_operations or self.is_dry_run():
            self._io.writeln(
                f'  - Removing <info>{operation.package.name}</> '
                f'(<comment>{operation.package.full_pretty_version}</>)'
            )

        if not self._execute_operations:
            return

        self._installer.remove(operation.package)

    def _populate_local_repo(self, local_repo, ops, locked_repository):
        # Add all locked packages from the lock and go from there
        for package in locked_repository.packages:
            local_repo.add_package(package)

        # Now, walk through all operations and add/remove/update accordingly
        for op in ops:
            if isinstance(op, Update):
                package = op.target_package
            else:
                package = op.package

            acted_on = False
            for pkg in local_repo.packages:
                if pkg.name == package.name:
                    # The package we operate on is in the local repo
                    if op.job_type == 'update':
                        if pkg.version == package.version:
                            break

                        local_repo.remove_package(pkg)
                        local_repo.add_package(op.target_package)
                    elif op.job_type == 'uninstall':
                        local_repo.remove_package(op.package)

                    acted_on = True

            if not acted_on:
                local_repo.add_package(package)

    def _get_operations_from_lock(self,
                                  locked_repository: Repository
                                  ) -> List[Operation]:
        installed_repo = InstalledRepository.load(self._io.venv)
        ops = []

        for locked in locked_repository.packages:
            is_installed = False
            for installed in installed_repo.packages:
                if locked.name == installed.name:
                    is_installed = True
                    if locked.category == 'dev' and not self.is_dev_mode():
                        ops.append(Uninstall(locked))
                    elif locked.version != installed.version:
                        ops.append(Update(
                            installed, locked
                        ))

            if not is_installed:
                ops.append(Install(locked))

        return ops

    def _get_installer(self) -> BaseInstaller:
        return PipInstaller(self._io.venv, self._io)
