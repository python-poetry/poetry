from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


def try_hardlink(src: Path, dst: Path) -> bool:
    """
    Try to create a hardlink from src to dst.

    Returns True if hardlink was successfully created, False otherwise.
    """
    try:
        # Check if src and dst are on the same filesystem
        if src.stat().st_dev != dst.parent.stat().st_dev:
            return False

        # Ensure parent directory exists
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Create hardlink
        src.link_to(dst)
        return True
    except (OSError, NotImplementedError, FileNotFoundError):
        return False


def try_reflink(src: Path, dst: Path) -> bool:
    """
    Try to create a reflink (copy-on-write) from src to dst.

    Returns True if reflink was successfully created, False otherwise.
    """
    try:
        # Ensure parent directory exists
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Try platform-specific reflink methods
        if hasattr(os, 'reflink'):
            # Linux (btrfs, xfs, ocfs2, etc.)
            with src.open('rb') as fsrc, dst.open('wb') as fdst:
                os.reflink(fsrc.fileno(), fdst.fileno())
            return True

        # Try shutil.copyfile with follow_symlinks=False for potential reflink
        shutil.copyfile(src, dst, follow_symlinks=False)

        # Check if it was actually a reflink by comparing inodes
        # (only works if both files are on the same filesystem)
        if src.stat().st_ino == dst.stat().st_ino:
            return True

        # Not a reflink, clean up
        dst.unlink()
        return False

    except (OSError, NotImplementedError, AttributeError, FileNotFoundError):
        return False


def copy_file(src: Path, dst: Path, is_executable: bool = False) -> None:
    """
    Copy a file from src to dst, preserving executable permissions.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Copy the file
    shutil.copy2(src, dst, follow_symlinks=True)

    # Set executable permission if requested
    if is_executable:
        current_mode = dst.stat().st_mode
        dst.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def link_or_copy(
    src: Path,
    dst: Path,
    *,
    link_mode: str = "copy",
    is_executable: bool = False,
    force_copy: bool = False,
) -> None:
    """
    Link or copy a file using the specified link mode.

    Args:
        src: Source file path
        dst: Destination file path
        link_mode: One of "copy", "hardlink", "reflink"
        is_executable: Whether to set executable permissions
        force_copy: Force copy even if link_mode is not "copy"
    """
    if force_copy:
        copy_file(src, dst, is_executable)
        return

    # Try link modes in order of preference
    if link_mode == "reflink":
        if try_reflink(src, dst):
            return
        # Fall through to hardlink
        link_mode = "hardlink"

    if link_mode == "hardlink":
        if try_hardlink(src, dst):
            return
        # Fall through to copy
        link_mode = "copy"

    # Final fallback: copy
    copy_file(src, dst, is_executable)