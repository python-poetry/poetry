# -*- coding: utf-8 -*-
from __future__ import division

import itertools
import os
import threading

from concurrent.futures import ThreadPoolExecutor
from functools import partial
from subprocess import CalledProcessError

from requests import Session

from poetry.core.packages.file_dependency import FileDependency
from poetry.core.packages.utils.link import Link
from poetry.io.null_io import NullIO
from poetry.locations import CACHE_DIR
from poetry.puzzle.operations.install import Install
from poetry.puzzle.operations.operation import Operation
from poetry.puzzle.operations.uninstall import Uninstall
from poetry.puzzle.operations.update import Update
from poetry.utils._compat import OrderedDict
from poetry.utils._compat import Path
from poetry.utils._compat import cpu_count
from poetry.utils.helpers import safe_rmtree

from .chef import Chef
from .chooser import Chooser


def take(n, iterable):
    return list(itertools.islice(iterable, n))


def chunked(iterable, n):
    return iter(partial(take, n, iter(iterable)), [])


class Executor(object):
    def __init__(self, env, pool, io, parallel=True):
        self._env = env
        self._io = io
        self._dry_run = False
        self._enabled = True
        self._verbose = False
        self._chef = Chef(self._env)
        self._chooser = Chooser(pool, self._env)

        if parallel:
            # This should be directly handled by ThreadPoolExecutor
            # however, on some systems the number of CPUs cannot be determined
            # (it raises a NotImplementedError), so, in this case, we assume
            # that the system only has one CPU.
            try:
                self._max_workers = cpu_count() + 4
            except NotImplementedError:
                self._max_workers = 5
        else:
            self._max_workers = 1

        self._executor = ThreadPoolExecutor(max_workers=self._max_workers)
        self._cache_dir = Path(CACHE_DIR) / "artifacts"
        self._total_operations = 0
        self._executed_operations = 0
        self._sections = OrderedDict()
        self._lock = threading.Lock()

    def supports_fancy_output(self):  # type: () -> bool
        return (
            self._io.supports_ansi() and not self._io.is_debug() and not self._dry_run
        )

    def disable(self):
        self._enabled = False

        return self

    def dry_run(self, dry_run=True):
        self._dry_run = dry_run

        return self

    def verbose(self, verbose=True):
        self._verbose = verbose

        return self

    def execute(self, operations):
        self._total_operations = len(operations)

        if operations and (self._enabled or self._dry_run):
            self._display_summary(operations)

        # We group operations by priority

        groups = itertools.groupby(operations, key=lambda o: -o.priority)
        i = 0
        self._sections = OrderedDict()
        self._last_write_times = OrderedDict()
        for _, group in groups:
            for chunk in chunked(group, self._max_workers):
                tasks = []
                for operation in chunk:
                    if id(operation) not in self._sections:
                        if self.supports_fancy_output() and self._should_write_operation(
                            operation
                        ):
                            self._lock.acquire()
                            self._sections[id(operation)] = self._io.section()
                            self._sections[id(operation)].write_line(
                                "  <fg=blue;options=bold>•</> {message}".format(
                                    message=self.get_operation_message(operation),
                                ),
                            )
                            self._lock.release()

                for operation in chunk:
                    tasks.append(
                        self._executor.submit(self._execute_operation, operation)
                    )
                    i += 1

                [t.result() for t in tasks]

    def _write(self, operation, line):
        self._lock.acquire()
        section = self._sections[id(operation)]
        section.output.clear()
        section.write(line)
        self._lock.release()

    def _execute_operation(self, operation):
        method = operation.job_type

        operation_message = self.get_operation_message(operation)
        if operation.skipped:
            if self._verbose and (self._enabled or self._dry_run):
                self._write(
                    operation,
                    "  <fg=yellow;options=bold>•</> {message}: <fg=yellow>Skipped</> ({reason})".format(
                        message=operation_message, reason=operation.skip_reason,
                    ),
                )

            return

        if not self._enabled or self._dry_run:
            self._io.write_line(
                "  <fg=blue;options=bold>•</> {message}".format(
                    message=operation_message,
                )
            )

            return

        getattr(self, "_execute_{}".format(method))(operation)

        message = "  <fg=green;options=bold>•</> {message}".format(
            message=self.get_operation_message(operation, done=True),
        )
        self._write(operation, message)

        self._executed_operations += 1

    def run(self, *args, **kwargs):  # type: (...) -> str
        return self._env.run("python", "-m", "pip", *args, **kwargs)

    def get_operation_message(self, operation, done=False):
        operation_color = "c2"

        if done:
            operation_color = "success"

        if operation.job_type == "install":
            return "Installing <c1>{}</c1> (<{}>{}</>)".format(
                operation.package.name,
                operation_color,
                operation.package.full_pretty_version,
            )

        if operation.job_type == "uninstall":
            return "Removing <c1>{}</c1> (<{}>{}</>)".format(
                operation.package.name,
                operation_color,
                operation.package.full_pretty_version,
            )

        if operation.job_type == "update":
            return "Updating <c1>{}</c1> (<c2>{}</c2> -> <{}>{}</>)".format(
                operation.initial_package.name,
                operation.initial_package.full_pretty_version,
                operation_color,
                operation.target_package.full_pretty_version,
            )

        return ""

    def _display_summary(self, operations):
        installs = 0
        updates = 0
        uninstalls = 0
        skipped = 0
        for op in operations:
            if op.skipped:
                skipped += 1
                continue

            if op.job_type == "install":
                installs += 1
            elif op.job_type == "update":
                updates += 1
            elif op.job_type == "uninstall":
                uninstalls += 1

        if not installs and not updates and not uninstalls and not self._verbose:
            self._io.write_line("")
            self._io.write_line("No dependencies to install or update")

            return

        self._io.write_line("")
        self._io.write_line(
            "<b>Package operations</b>: "
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
                if skipped and self._verbose
                else "",
            )
        )
        self._io.write_line("")

    def _execute_install(self, operation):  # type: (Install) -> None
        self._install(operation)

    def _execute_update(self, operation):  # type: (Update) -> None
        self._update(operation)

    def _execute_uninstall(self, operation):  # type: (Uninstall) -> None
        message = "  <fg=blue;options=bold>•</> {message}: <info>Removing...</info>".format(
            message=self.get_operation_message(operation),
        )
        self._write(operation, message)

        self._remove(operation)

    def _install(self, operation):
        package = operation.package
        if package.source_type == "directory":
            self._install_directory(operation)

            return

        if package.source_type == "git":
            self._install_git(operation)

            return

        archive = self._download(operation)
        operation_message = self.get_operation_message(operation)
        message = "  <fg=blue;options=bold>•</> {message}: <info>Installing...</info>".format(
            message=operation_message,
        )
        self._write(operation, message)

        args = ["install", "--no-deps", str(archive)]
        if operation.job_type == "update":
            args.insert(2, "-U")

        self.run(*args)

    def _update(self, operation):
        return self._install(operation)

    def _remove(self, operation):
        package = operation.package

        # If we have a VCS package, remove its source directory
        if package.source_type == "git":
            src_dir = self._env.path / "src" / package.name
            if src_dir.exists():
                safe_rmtree(str(src_dir))

        try:
            self.run("uninstall", package.name, "-y")
        except CalledProcessError as e:
            if "not installed" in str(e):
                return

            raise

    def _install_directory(self, operation):
        from poetry.factory import Factory
        from poetry.utils.toml_file import TomlFile

        package = operation.package
        operation_message = self.get_operation_message(operation)

        message = "  <fg=blue;options=bold>•</> {message}: <info>Building...</info>".format(
            message=operation_message,
        )
        self._write(operation, message)

        if package.root_dir:
            req = os.path.join(package.root_dir, package.source_url)
        else:
            req = os.path.realpath(package.source_url)

        args = ["install", "--no-deps", "-U"]

        pyproject = TomlFile(os.path.join(req, "pyproject.toml"))

        has_poetry = False
        has_build_system = False
        if pyproject.exists():
            pyproject_content = pyproject.read()
            has_poetry = (
                "tool" in pyproject_content and "poetry" in pyproject_content["tool"]
            )
            # Even if there is a build system specified
            # some versions of pip (< 19.0.0) don't understand it
            # so we need to check the version of pip to know
            # if we can rely on the build system
            pip_version = self._env.pip_version
            pip_version_with_build_system_support = pip_version.__class__(19, 0, 0)
            has_build_system = (
                "build-system" in pyproject_content
                and pip_version >= pip_version_with_build_system_support
            )

        if has_poetry:
            package_poetry = Factory().create_poetry(pyproject.parent)
            if package.develop and not package_poetry.package.build_script:
                from poetry.masonry.builders.editable import EditableBuilder

                # This is a Poetry package in editable mode
                # we can use the EditableBuilder without going through pip
                # to install it, unless it has a build script.
                builder = EditableBuilder(package_poetry, self._env, NullIO())
                builder.build()

                return
            elif not has_build_system or package_poetry.package.build_script:
                from poetry.core.masonry.builders.sdist import SdistBuilder

                # We need to rely on creating a temporary setup.py
                # file since the version of pip does not support
                # build-systems
                # We also need it for non-PEP-517 packages
                builder = SdistBuilder(package_poetry)

                with builder.setup_py():
                    if package.develop:
                        args.append("-e")

                    args.append(req)

                    return self.run(*args)

        if package.develop:
            args.append("-e")

        args.append(req)

        return self.run(*args)

    def _install_git(self, operation):
        from poetry.core.vcs import Git

        package = operation.package
        operation_message = self.get_operation_message(operation)

        message = "  <fg=blue;options=bold>•</> {message}: <info>Cloning...</info>".format(
            message=operation_message,
        )
        self._write(operation, message)

        src_dir = self._env.path / "src" / package.name
        if src_dir.exists():
            safe_rmtree(str(src_dir))

        src_dir.parent.mkdir(exist_ok=True)

        git = Git()
        git.clone(package.source_url, src_dir)
        git.checkout(package.source_reference, src_dir)

        # Now we just need to install from the source directory
        package.source_url = str(src_dir)

        self._install_directory(operation)

    def _download(self, operation):  # type: (Operation) -> Path
        package = operation.package
        cache_dir = self._cache_dir / package.name
        cache_dir.mkdir(parents=True, exist_ok=True)

        link = self._chooser.choose_for(package)

        archive = cache_dir / link.filename
        if not archive.exists():
            try:
                archive = self._download_archive(operation, link, archive)
            except BaseException:
                archive.unlink(missing_ok=True)

                raise

            # TODO: Check readability of the created archive

            if not link.is_wheel:
                archive = self._chef.prepare(archive)

        if package.files:
            archive_hash = "sha256:" + FileDependency(package.name, archive).hash()
            if archive_hash not in {f["hash"] for f in package.files}:
                raise RuntimeError(
                    "Invalid hash for {} using archive {}".format(package, archive.name)
                )

        return archive

    def _download_archive(
        self, operation, link, archive
    ):  # type: (Operation, Link, Path) -> Path
        session = Session()
        response = session.get(link.url, stream=True)
        response.raise_for_status()
        wheel_size = response.headers.get("content-length")
        operation_message = self.get_operation_message(operation)
        message = "  <fg=blue;options=bold>•</> {message}: <info>Downloading...</>".format(
            message=operation_message,
        )
        progress = None
        if not self.supports_fancy_output() or wheel_size is None:
            self._io.write_line(message)
        else:
            from clikit.ui.components.progress_bar import ProgressBar

            progress = ProgressBar(
                self._sections[id(operation)].output, max=int(wheel_size)
            )
            progress.set_format(message + " (<b>%percent%%</b>)")

        if progress:
            self._lock.acquire()
            progress.start()
            self._lock.release()

        done = 0
        with archive.open("wb") as f:
            for chunk in response.iter_content(chunk_size=4096):
                if not chunk:
                    break

                done += len(chunk)

                if progress:
                    self._lock.acquire()
                    progress.set_progress(done)
                    self._lock.release()

                f.write(chunk)

        if progress:
            self._lock.acquire()
            progress.finish()
            self._lock.release()

        return archive

    def _should_write_operation(self, operation):  # type: (Operation) -> bool
        if not operation.skipped:
            return True

        return self._dry_run or self._verbose
