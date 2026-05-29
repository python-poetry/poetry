"""Builtin package uninstaller.

Entry point is the ``uninstall_distribution`` function.

Adapted from pip's ``pip._internal.req.req_uninstall`` so Poetry can uninstall
packages without invoking ``pip uninstall`` as a subprocess. The module is
self-contained and does not import from pip.

Most methods and classes are borrowed from pip with minimal adaptations.
The env-prefix and stdlib guards that pip applies in
``UninstallPathSet.from_dist`` have been moved to ``uninstall_distribution``,
along with all legacy-install branches (setuptools flat installs,
easy_install eggs, develop-egg links) being dropped entirely — Poetry should
only see modern ``.dist-info`` installs.

ATTENTION: Do not convert os.path to pathlib lightly in this module!
    pathlib is often slower and some path operations
    are called for each file that has to be removed.
"""

from __future__ import annotations

import errno
import functools
import itertools
import logging
import os
import shutil
import tempfile

from importlib.util import cache_from_source
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from poetry.utils._compat import is_relative_to


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterable
    from collections.abc import Iterator
    from importlib import metadata
    from importlib.metadata import PackagePath

    from poetry.utils.env import Env


logger = logging.getLogger(__name__)


def _normalize_path(path: str | Path, resolve_symlinks: bool = True) -> str:
    path = os.path.expanduser(path)
    path = os.path.realpath(path) if resolve_symlinks else os.path.abspath(path)
    return os.path.normcase(path)


def _renames(old: str, new: str) -> None:
    """Like os.renames(), but handles renaming across devices."""
    # Implementation borrowed from os.renames().
    head, tail = os.path.split(new)
    if head and tail and not os.path.exists(head):
        os.makedirs(head)

    shutil.move(old, new)

    head, tail = os.path.split(old)
    if head and tail:
        try:  # noqa: SIM105 (performance)
            os.removedirs(head)
        except OSError:
            pass


class _TempDirectory:
    """Owns and cleans up a temporary directory."""

    def __init__(self) -> None:
        self._path = self._create()
        logger.debug("Created temporary directory: %s", self._path)

    def _create(self) -> str:
        """Create a temporary directory and store its path in self.path"""
        return tempfile.mkdtemp(prefix="poetry-uninstall-")

    @property
    def path(self) -> str:
        return self._path

    def cleanup(self) -> None:
        if os.path.exists(self._path):
            shutil.rmtree(self._path, ignore_errors=True)


class _AdjacentTempDirectory(_TempDirectory):
    """Creates a temporary directory adjacent to ``original``."""

    LEADING_CHARS = "-~.=%0123456789"

    def __init__(self, original: str) -> None:
        self.original = original.rstrip("/\\")
        super().__init__()

    def _create(self) -> str:
        root, name = os.path.split(self.original)
        for candidate in self._generate_names(name):
            path = os.path.join(root, candidate)
            try:
                os.mkdir(path)
            except OSError as ex:
                # Continue if the name exists already
                if ex.errno != errno.EEXIST:
                    raise
            else:
                return path
        return super()._create()

    @classmethod
    def _generate_names(cls, name: str) -> Iterator[str]:
        """Generates a series of temporary names.

        The algorithm replaces the leading characters in the name
        with ones that are valid filesystem characters, but are not
        valid package names (for both Python and pip definitions of
        package).
        """
        for i in range(1, len(name)):
            for candidate in itertools.combinations_with_replacement(
                cls.LEADING_CHARS, i - 1
            ):
                new_name = "~" + "".join(candidate) + name[i:]
                if new_name != name:
                    yield new_name

        # If we make it this far, we will have to make a longer name
        for i in range(len(cls.LEADING_CHARS)):
            for candidate in itertools.combinations_with_replacement(
                cls.LEADING_CHARS, i
            ):
                new_name = "~" + "".join(candidate) + name
                if new_name != name:
                    yield new_name


def _unique(fn: Callable[..., Iterator[Any]]) -> Callable[..., Iterator[Any]]:
    @functools.wraps(fn)
    def unique(*args: Any, **kw: Any) -> Iterator[Any]:
        seen: set[Any] = set()
        for item in fn(*args, **kw):
            if item not in seen:
                seen.add(item)
                yield item

    return unique


@_unique
def _uninstallation_paths(
    dist_files: list[PackagePath], location: str | Path
) -> Iterator[str]:
    """Yield all uninstallation paths declared in the distribution's RECORD.

    For each .py file in RECORD, also yield the sibling .pyc/.pyo. The
    ``UninstallPathSet.add`` method handles ``__pycache__`` discovery.
    """
    for entry in dist_files:
        path = os.path.join(location, str(entry))
        yield path
        if path.endswith(".py"):
            dn, fn = os.path.split(path)
            base = fn[:-3]
            yield os.path.join(dn, base + ".pyc")
            yield os.path.join(dn, base + ".pyo")


def compress_for_rename(paths: Iterable[str]) -> set[str]:
    """Returns a set containing the paths that need to be renamed.

    This set may include directories when the original sequence of paths
    included every file on disk.
    """
    case_map = {os.path.normcase(p): p for p in paths}
    remaining = set(case_map)
    unchecked = sorted({os.path.split(p)[0] for p in case_map.values()}, key=len)
    wildcards: set[str] = set()

    def norm_join(*a: str) -> str:
        return os.path.normcase(os.path.join(*a))

    for root in unchecked:
        if any(os.path.normcase(root).startswith(w) for w in wildcards):
            # This directory has already been handled.
            continue

        all_files: set[str] = set()
        all_subdirs: set[str] = set()
        for dirname, subdirs, files in os.walk(root):
            all_subdirs.update(norm_join(root, dirname, d) for d in subdirs)
            all_files.update(norm_join(root, dirname, f) for f in files)
        # If all the files we found are in our remaining set of files to
        # remove, then remove them from the latter set and add a wildcard
        # for the directory.
        if not (all_files - remaining):
            remaining.difference_update(all_files)
            remaining.difference_update(all_subdirs)
            wildcards.add(root + os.sep)

    return set(map(case_map.__getitem__, remaining)) | wildcards


class StashedUninstallPathSet:
    """A set of file rename operations to stash files while
    tentatively uninstalling them."""

    def __init__(self) -> None:
        # Mapping from source file root to [Adjacent]TempDirectory
        # for files under that directory.
        self._save_dirs: dict[str, _TempDirectory] = {}
        # (old path, new path) tuples for each move that may need
        # to be undone.
        self._moves: list[tuple[str, str]] = []

    def _get_directory_stash(self, path: str) -> str:
        """Stashes a directory.

        Directories are stashed adjacent to their original location if
        possible, or else moved/copied into the user's temp dir."""
        save_dir: _TempDirectory
        try:
            save_dir = _AdjacentTempDirectory(path)
        except OSError:
            save_dir = _TempDirectory()
        self._save_dirs[os.path.normcase(path)] = save_dir
        return save_dir.path

    def _get_file_stash(self, path: str) -> str:
        """Stashes a file.

        If no root has been provided, one will be created for the directory
        in the user's temp directory."""
        path = os.path.normcase(path)
        head, old_head = os.path.dirname(path), None

        while head != old_head:
            try:
                save_dir = self._save_dirs[head]
                break
            except KeyError:
                pass
            head, old_head = os.path.dirname(head), head
        else:
            # Did not find any suitable root
            head = os.path.dirname(path)
            save_dir = _TempDirectory()
            self._save_dirs[head] = save_dir

        relpath = os.path.relpath(path, head)
        if relpath and relpath != os.path.curdir:
            return os.path.join(save_dir.path, relpath)
        return save_dir.path

    def stash(self, path: str) -> str:
        """Stashes the directory or file and returns its new location.
        Handle symlinks as files to avoid modifying the symlink targets.
        """
        path_is_dir = os.path.isdir(path) and not os.path.islink(path)
        if path_is_dir:
            new_path = self._get_directory_stash(path)
        else:
            new_path = self._get_file_stash(path)

        self._moves.append((path, new_path))
        if path_is_dir and os.path.isdir(new_path):
            # If we're moving a directory, we need to
            # remove the destination first or else it will be
            # moved to inside the existing directory.
            # We just created new_path ourselves, so it will
            # be removable.
            os.rmdir(new_path)
        _renames(path, new_path)
        return new_path

    def commit(self) -> None:
        """Commits the uninstall by removing stashed files."""
        for save_dir in self._save_dirs.values():
            save_dir.cleanup()
        self._moves = []
        self._save_dirs = {}

    def rollback(self) -> None:
        """Undoes the uninstall by moving stashed files back."""
        for p in self._moves:
            logger.debug("Moving to %s\n from %s", *p)

        for new_path, path in self._moves:
            try:
                logger.debug("Replacing %s from %s", new_path, path)
                if os.path.isfile(new_path) or os.path.islink(new_path):
                    os.unlink(new_path)
                elif os.path.isdir(new_path):
                    shutil.rmtree(new_path)
                _renames(path, new_path)
            except OSError as ex:
                logger.error("Failed to restore %s", new_path)
                logger.debug("Exception: %s", ex)

        self.commit()

    @property
    def can_rollback(self) -> bool:
        return bool(self._moves)


class UninstallPathSet:
    """A set of file paths to be removed when uninstalling a distribution."""

    def __init__(self, dist: metadata.Distribution, env_path: Path) -> None:
        self._paths: set[str] = set()
        self._refuse: set[str] = set()
        # Read identifying metadata eagerly so log messages still work after
        # remove() stashes the .dist-info directory.
        self._dist_name = dist.name
        self._dist_version = dist.metadata["Version"]
        # Append os.sep so the startswith() check in _permitted() does not
        # spuriously match a sibling directory whose name starts with env_path
        # (e.g. env_path="/tmp/.venv" would otherwise match "/tmp/.venv-other").
        self._env_prefix = _normalize_path(env_path) + os.sep
        self._moved_paths = StashedUninstallPathSet()
        # Create local cache of normalize_path results. Creating an UninstallPathSet
        # can result in hundreds/thousands of redundant calls to normalize_path with
        # the same args, which hurts performance.
        self._normalize_path_cached = functools.lru_cache(_normalize_path)

    @property
    def paths(self) -> set[str]:
        return self._paths

    @property
    def refused(self) -> set[str]:
        return self._refuse

    def _permitted(self, path: str) -> bool:
        """Return True if ``path`` is inside the env prefix."""
        return path.startswith(self._env_prefix)

    def add(self, path: str | Path) -> None:
        head, tail = os.path.split(path)

        # We normalize the head to resolve parent directory symlinks, but not
        # the tail, since we only want to uninstall symlinks, not their targets.
        norm_path = os.path.join(
            self._normalize_path_cached(head), os.path.normcase(tail)
        )

        if not os.path.exists(norm_path):
            return
        if self._permitted(norm_path):
            self._paths.add(norm_path)
        else:
            self._refuse.add(norm_path)

        # ``__pycache__`` entries may not exist until after RECORD is written.
        if os.path.splitext(norm_path)[1] == ".py":
            self.add(cache_from_source(norm_path))

    def remove(self) -> None:
        """Stash every path so the uninstall can be committed or rolled back."""
        if not self._paths:
            logger.warning(
                "Cannot uninstall '%s'. No files were found to uninstall.",
                self._dist_name,
            )
            return

        logger.debug("Uninstalling %s %s.", self._dist_name, self._dist_version)

        moved = self._moved_paths
        for_rename = compress_for_rename(self._paths)

        for path in sorted(for_rename):
            moved.stash(path)
            logger.debug("Removing file or directory %s", path)

        logger.debug(
            "Successfully uninstalled %s %s", self._dist_name, self._dist_version
        )

    def rollback(self) -> None:
        """Undo a prior remove()."""
        if not self._moved_paths.can_rollback:
            logger.error(
                "Cannot roll back %s; was not uninstalled",
                self._dist_name,
            )
            return
        logger.info("Rolling back uninstall of %s", self._dist_name)
        self._moved_paths.rollback()

    def commit(self) -> None:
        """Finalize the uninstall; rollback will no longer be possible."""
        self._moved_paths.commit()


def uninstall_distribution(env: Env, package_name: str) -> UninstallPathSet | None:
    """Uninstall ``package_name`` from ``env``.

    Returns the pathset (the caller is responsible for calling ``.commit()``
    or ``.rollback()``), or ``None`` if the package is not installed.
    """
    dist = next(iter(env.site_packages.distributions(name=package_name)), None)

    if dist is None:
        logger.warning("Skipping %s as it is not installed.", package_name)
        return None

    logger.debug("Found existing installation: %s", package_name)

    dist_info_path: Path = dist._path  # type: ignore[attr-defined]
    dist_parent = dist_info_path.parent

    if not is_relative_to(dist_parent, env.path):
        logger.error(
            "Not uninstalling %s at %s, outside environment %s",
            dist.name,
            dist_parent,
            env.path,
        )
        return None

    stdlib_paths = {
        Path(p) for p in {env.paths.get("stdlib"), env.paths.get("platstdlib")} if p
    }
    if dist_parent in stdlib_paths:
        logger.error(
            "Not uninstalling %s at %s, as it is in the standard library.",
            dist.name,
            dist_parent,
        )
        return None

    dist_files = dist.files
    if dist_files is None:
        logger.error(
            "Cannot uninstall %s: RECORD file is missing or unreadable.",
            dist.name,
        )
        return None

    path_set = UninstallPathSet(dist, env.path)
    for path in _uninstallation_paths(dist_files, dist_parent):
        path_set.add(path)

    path_set.remove()

    return path_set
