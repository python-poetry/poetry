from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

from poetry.utils.wheel import Wheel

if TYPE_CHECKING:
    from collections.abc import Iterable


class UnpackedWheelStore:
    """
    Store for unpacked wheel files that can be hardlinked into virtual environments.

    Wheels are stored in a content-addressed directory structure based on their
    name, version, and tags to enable safe sharing across multiple environments.
    """

    def __init__(self, cache_dir: Path) -> None:
        """
        Initialize the unpacked wheel store.

        Args:
            cache_dir: Base cache directory (typically ~/.cache/pypoetry)
        """
        self.cache_dir = cache_dir / "unpacked"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_store_path(self, wheel: Wheel) -> Path:
        """
        Get the store path for a wheel.

        Args:
            wheel: Wheel object

        Returns:
            Path to the unpacked wheel directory in the store
        """
        # Create a content-addressed key
        wheel_key = {
            "name": wheel.name,
            "version": wheel.version,
            "tags": sorted(wheel.tags),
        }
        key_json = json.dumps(wheel_key, sort_keys=True, separators=(",", ":"))
        key_hash = hashlib.sha256(key_json.encode("utf-8")).hexdigest()

        # Use first 16 characters of hash for directory name
        return self.cache_dir / key_hash[:16]

    def extract_wheel(self, wheel_path: Path) -> Path:
        """
        Extract a wheel file to the store.

        Args:
            wheel_path: Path to the wheel file

        Returns:
            Path to the extracted wheel directory
        """
        wheel = Wheel(wheel_path.name)
        store_path = self.get_store_path(wheel)

        # Check if already extracted
        if store_path.exists():
            # Verify it's complete by checking for a marker file
            marker_file = store_path / ".extracted"
            if marker_file.exists():
                return store_path

            # Incomplete extraction, clean up
            shutil.rmtree(store_path, ignore_errors=True)

        # Create store directory
        store_path.mkdir(parents=True, exist_ok=True)

        try:
            # Extract wheel contents
            with zipfile.ZipFile(wheel_path, "r") as zf:
                zf.extractall(store_path)

            # Create marker file to indicate successful extraction
            (store_path / ".extracted").touch()

            return store_path

        except Exception:
            # Clean up on failure
            shutil.rmtree(store_path, ignore_errors=True)
            raise

    def get_wheel_file_path(self, store_path: Path, wheel_name: str) -> Path:
        """
        Get the path to the wheel file within the store.

        Args:
            store_path: Path to the extracted wheel directory
            wheel_name: Name of the wheel file

        Returns:
            Path to the wheel file
        """
        return store_path / wheel_name

    def list_entries(self) -> Iterable[Path]:
        """
        List all entries in the unpacked wheel store.

        Returns:
            Iterable of store entry paths
        """
        if not self.cache_dir.exists():
            return []

        return self.cache_dir.iterdir()

    def prune_unreferenced(self) -> int:
        """
        Prune store entries that are no longer referenced by any venv.

        Uses link counts to determine if files are still in use.

        Returns:
            Number of entries pruned
        """
        pruned_count = 0

        for store_entry in self.list_entries():
            if not store_entry.is_dir():
                continue

            # Check if this is a valid store entry
            marker_file = store_entry / ".extracted"
            if not marker_file.exists():
                continue

            # Check link counts of files in the store
            try:
                # Get all files in the store entry
                files = list(store_entry.rglob("*"))
                if not files:
                    continue

                # Check if any file has link count > 1 (referenced by venv)
                is_referenced = False
                for file_path in files:
                    if file_path.is_file():
                        try:
                            link_count = file_path.stat().st_nlink
                            if link_count > 1:
                                is_referenced = True
                                break
                        except (OSError, FileNotFoundError):
                            continue

                # Only prune if no files are referenced
                if not is_referenced:
                    shutil.rmtree(store_entry)
                    pruned_count += 1

            except OSError:
                # Entry is likely in use or corrupted, skip it
                continue

        return pruned_count

    def clear(self) -> None:
        """
        Clear the entire unpacked wheel store.
        """
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)