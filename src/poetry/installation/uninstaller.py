"""Builtin package uninstaller.

Entry point is the ``uninstall_distribution`` function.

Adapted from pip's ``pip._internal.req.req_uninstall`` so Poetry can uninstall
packages without invoking ``pip uninstall`` as a subprocess. The module is
self-contained and does not import from pip.

Most methods and classes are borrowed from pip with minimal adaptations.
The env-prefix and stdlib guards that pip applies in
``UninstallPathSet.from_dist`` have been moved to ``uninstall_distribution``,
along with all legacy-install branches (setuptools flat installs,
easy_install eggs, develop-egg links) being dropped entirely - Poetry should
only see modern ``.dist-info`` installs.

Unlike pip, this uninstaller removes files directly instead of stashing them
for a possible rollback: it raises if a file cannot be removed (a file that is
already missing is fine) and removes the ``.dist-info`` directory last, so that
a failed, aborted uninstall can simply be triggered again - the ``RECORD`` file
inside ``.dist-info`` is what tells us which files to remove.

Files are deleted one by one and the directories they leave empty are removed
afterwards (deepest first), stopping at the install-scheme roots (site-packages,
scripts, ...) which are never removed even when they end up empty. The
``.dist-info`` directory belongs solely to one distribution, so it is removed
whole with a single ``rmtree`` at the very end.

ATTENTION: Do not convert os.path to pathlib lightly in this module!
    pathlib is often slower and some path operations
    are called for each file that has to be removed.
"""

from __future__ import annotations

import contextlib
import functools
import logging
import os

from pathlib import Path
from typing import TYPE_CHECKING

from poetry.utils.helpers import remove_directory


if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Iterator
    from importlib import metadata

    from poetry.utils.env import Env


logger = logging.getLogger(__name__)


def _normalize_path(path: str | Path, resolve_symlinks: bool = True) -> str:
    path = os.path.expanduser(path)
    path = os.path.realpath(path) if resolve_symlinks else os.path.abspath(path)
    return os.path.normcase(path)


def _safe_listdir(path: str) -> tuple[str, ...]:
    """Return directory entries (empty if it is missing or not a directory)."""
    try:
        return tuple(os.listdir(path))
    except OSError:
        return ()


class UninstallPathSet:
    """A set of file paths to be removed when uninstalling a distribution."""

    def __init__(
        self,
        dist: metadata.Distribution,
        env_path: Path,
        protected_dirs: set[str] | None = None,
    ) -> None:
        self._paths: set[str] = set()
        self._refuse: set[str] = set()
        # Read identifying metadata eagerly so log messages still work after
        # remove() deletes the .dist-info directory.
        self._dist_name = dist.name
        self._dist_version = dist.metadata["Version"]
        # Append os.sep so the startswith() check in _permitted() does not
        # spuriously match a sibling directory whose name starts with env_path
        # (e.g. env_path="/tmp/.venv" would otherwise match "/tmp/.venv-other").
        self._env_prefix = _normalize_path(env_path) + os.sep
        # Create local cache of normalize_path results. Creating an UninstallPathSet
        # can result in hundreds/thousands of redundant calls to normalize_path with
        # the same args, which hurts performance.
        self._normalize_path_cached = functools.lru_cache(maxsize=None)(_normalize_path)
        # Cache __pycache__ listings so a directory is scanned only once even
        # though add() is called for every .py file it contains. This is safe
        # because we are robust against files that may have been deleted
        # in the meantime.
        self._listdir_cached = functools.lru_cache(maxsize=None)(_safe_listdir)
        # Normalized path of the .dist-info directory, so remove() can delete it
        # last (see remove() for why).
        dist_info_path: Path = dist._path  # type: ignore[attr-defined]
        self._dist_info = self._normalize_path_cached(str(dist_info_path))
        # Directories that must never be removed even when they end up empty.
        # Always protect the directory holding the .dist-info (the site-packages
        # dir); callers add the remaining install-scheme roots (scripts, data,
        # ...). Values are expected already normalized, like self._dist_info.
        self._protected: set[str] = {os.path.dirname(self._dist_info)}
        self._protected.update(protected_dirs or ())

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

        # ``__pycache__`` bytecode may not be listed in RECORD (it is often
        # compiled lazily on first import). Discover it for every source file.
        if os.path.splitext(norm_path)[1] == ".py":
            for pyc in self._pycache_files(norm_path):
                self.add(pyc)

    def _pycache_files(self, py_path: str) -> Iterator[str]:
        """Yield bytecode cache files for a source ``.py`` file.

        Bytecode lives in a sibling ``__pycache__`` directory named
        ``<stem>.<tag>.pyc`` (PEP 3147), where ``<tag>`` identifies the Python
        version/implementation that compiled it. The target environment may run
        a different Python version than the interpreter executing Poetry, so we
        match bytecode compiled for *any* version - not just the current
        interpreter's ``cache_from_source`` tag.

        The directory listing is memoized (``_listdir_cached``) so that a
        ``__pycache__`` is scanned only once even when many ``.py`` files in the
        same directory each trigger this lookup.
        """
        head, tail = os.path.split(py_path)
        pycache = os.path.join(head, "__pycache__")
        # ``tail`` is already normcased by the caller; match case-insensitively
        # against the on-disk names for Windows.
        prefix = os.path.normcase(tail[: -len(".py")]) + "."
        for name in self._listdir_cached(pycache):
            norm_name = os.path.normcase(name)
            if norm_name.startswith(prefix):
                yield os.path.join(pycache, name)

    def remove(self) -> None:
        """Remove every path, deleting the .dist-info directory last.

        The package's files are removed one by one and the directories they
        leave empty are pruned (deepest first), stopping at the protected
        install-scheme roots. The .dist-info directory is then removed whole in a
        single rmtree. A path that cannot be removed raises; a path that is
        already missing is ignored. The .dist-info directory is removed last so
        that, if removal fails partway through, the uninstall can simply be
        triggered again - its RECORD is what tells us which files to remove.
        """
        if not self._paths:
            logger.warning(
                "Cannot uninstall '%s'. No files were found to uninstall.",
                self._dist_name,
            )
            return

        logger.debug("Uninstalling %s %s.", self._dist_name, self._dist_version)

        parents: set[str] = set()
        deferred_dirs: list[str] = []
        # Remove the package's files first, so the .dist-info directory (and its
        # RECORD) survives a partial failure and the uninstall stays re-runnable.
        package_paths = {p for p in self._paths if not self._is_dist_info(p)}
        self._remove_files(sorted(package_paths), parents, deferred_dirs)

        # Remove any directory entries RECORD listed explicitly, deepest
        # first; a non-empty one is left in place. Actually, this should
        # not be possible, but it should not hurt for robustness.
        for path in sorted(deferred_dirs, key=len, reverse=True):
            with contextlib.suppress(OSError):
                os.rmdir(path)
            parents.add(os.path.dirname(path))

        # Remove the directories our files left empty.
        self._prune_empty_dirs(parents)

        # Finally remove the whole .dist-info directory in one call. It belongs
        # solely to this distribution, so nothing else lives there; this also
        # clears files an installer added without listing them in RECORD
        # (INSTALLER, REQUESTED, direct_url.json, licenses/, ...). Done last so a
        # failure above leaves RECORD intact for a re-run. The _permitted guard
        # keeps the "never remove anything outside the env prefix" invariant.
        # force=True so removal tolerates entries that vanish mid-walk (already
        # gone is fine) and read-only files, while still raising on real errors.
        if self._permitted(self._dist_info):
            remove_directory(Path(self._dist_info), force=True)

        logger.debug(
            "Successfully uninstalled %s %s", self._dist_name, self._dist_version
        )

    def _is_dist_info(self, path: str) -> bool:
        """Return True if ``path`` is the .dist-info directory or inside it."""
        norm = os.path.normcase(path.rstrip(os.sep))
        return norm == self._dist_info or norm.startswith(self._dist_info + os.sep)

    @staticmethod
    def _remove_files(
        paths: Iterable[str], parents: set[str], deferred_dirs: list[str]
    ) -> None:
        """Remove each file, recording the parent directory for later pruning.

        An already-missing path is ignored; a real directory (should not happen)
        is deferred for ``rmdir``; any other failure propagates so the
        caller can abort the operation. ``os.remove`` on a symlink-to-directory
        unlinks the link, not its target.
        """
        for path in paths:
            logger.debug("Removing file %s", path)
            try:
                os.remove(path)
            except FileNotFoundError:
                pass  # already gone - still prune its parent below
            except IsADirectoryError:
                # should not happen under normal circumstances
                deferred_dirs.append(path)
                continue
            except PermissionError:
                # Windows raises a PermissionError instead of a IsDirectoryError.
                if os.path.isdir(path):
                    # should not happen, just in case
                    deferred_dirs.append(path)
                    continue
                raise
            parents.add(os.path.dirname(path))

    def _prune_empty_dirs(self, dirs: set[str]) -> None:
        """Remove directories left empty, deepest first, climbing upward.

        Stops at a protected install-scheme directory and never climbs above the
        environment prefix, so site-packages / scripts are never removed even
        when they end up empty. ``dirs`` are normalized (parents of normalized
        ``_paths``), so they compare directly against ``_env_prefix`` and
        ``_protected``.
        """
        for d in sorted(dirs, key=len, reverse=True):
            while d.startswith(self._env_prefix) and d not in self._protected:
                try:
                    os.rmdir(d)
                except OSError:
                    break  # not empty (or already gone) - stop this chain
                d = os.path.dirname(d)


def uninstall_distribution(env: Env, package_name: str) -> UninstallPathSet | None:
    """Uninstall ``package_name`` from ``env``.

    Removes the package's files immediately (the .dist-info directory last).
    Raises if a file cannot be removed. Returns the pathset (useful for
    inspection/logging), or ``None`` if there was nothing to uninstall (package
    not installed, located outside the env, in the stdlib, or missing RECORD).
    """
    dist = next(iter(env.site_packages.distributions(name=package_name)), None)

    if dist is None:
        logger.warning("Skipping %s as it is not installed.", package_name)
        return None

    logger.debug("Found existing installation: %s", package_name)

    dist_info_path: Path = dist._path  # type: ignore[attr-defined]
    dist_parent = dist_info_path.parent

    # Normalize through _normalize_path (realpath + normcase) so these guards
    # resolve symlinks and case exactly the way UninstallPathSet._permitted()
    # does - otherwise a symlinked venv prefix could pass one check but fail the
    # other.
    norm_dist_parent = _normalize_path(dist_parent)
    norm_env_prefix = _normalize_path(env.path)

    # Append os.sep so a sibling directory whose name merely starts with the env
    # prefix (e.g. "/tmp/.venv-other" vs "/tmp/.venv") is not treated as inside.
    if not (
        norm_dist_parent == norm_env_prefix
        or norm_dist_parent.startswith(norm_env_prefix + os.sep)
    ):
        logger.error(
            "Not uninstalling %s at %s, outside environment %s",
            dist.name,
            dist_parent,
            env.path,
        )
        return None

    stdlib_paths = {
        _normalize_path(p)
        for p in {env.paths.get("stdlib"), env.paths.get("platstdlib")}
        if p
    }
    if norm_dist_parent in stdlib_paths:
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

    # Protect the env's install-scheme roots (site-packages, scripts, data, ...)
    # so the empty-directory pruning never removes them, even when emptied.
    protected_dirs = {_normalize_path(p) for p in env.paths.values() if p}
    protected_dirs.add(_normalize_path(env.path))

    path_set = UninstallPathSet(dist, env.path, protected_dirs=protected_dirs)
    for entry in dist_files:
        path_set.add(os.path.join(dist_parent, str(entry)))

    path_set.remove()

    return path_set
