from __future__ import annotations

from typing import TYPE_CHECKING

from cleo.helpers import option

from poetry.config.config import Config
from poetry.console.commands.command import Command
from poetry.installation.unpacked_wheel_store import UnpackedWheelStore


if TYPE_CHECKING:
    from cleo.io.inputs.option import Option


class CachePruneCommand(Command):
    name = "cache prune"
    description = "Prune unreferenced entries from the unpacked wheel store."

    options: list[Option] = [
        option(
            "dry-run",
            description="Show what would be pruned without actually deleting anything.",
            flag=True,
        ),
        option(
            "all",
            description="Prune all unreferenced entries (default behavior).",
            flag=True,
        ),
    ]

    def handle(self) -> int:
        config = Config.create()
        cache_dir = config.artifacts_cache_directory
        store = UnpackedWheelStore(cache_dir)

        self.line("<info>Checking unpacked wheel store for unreferenced entries...</info>")

        if not store.cache_dir.exists():
            self.line("No unpacked wheel store found.")
            return 0

        # List all entries
        entries = list(store.list_entries())
        if not entries:
            self.line("No entries found in unpacked wheel store.")
            return 0

        self.line(f"Found {len(entries)} entries in unpacked wheel store.")

        if self.option("dry-run"):
            self.line("\n<comment>Dry run - showing what would be pruned:</comment>")
            pruned_count = 0
            for entry in entries:
                if not entry.is_dir():
                    continue

                # Check if this is a valid store entry
                marker_file = entry / ".extracted"
                if not marker_file.exists():
                    continue

                # Check if any file has link count > 1 (referenced by venv)
                is_referenced = False
                try:
                    for file_path in entry.rglob("*"):
                        if file_path.is_file():
                            try:
                                link_count = file_path.stat().st_nlink
                                if link_count > 1:
                                    is_referenced = True
                                    break
                            except (OSError, FileNotFoundError):
                                continue
                except OSError:
                    continue

                if not is_referenced:
                    self.line(f"  Would prune: {entry.name}")
                    pruned_count += 1
                else:
                    self.line(f"  Would keep: {entry.name} (linked by other venvs)")

            self.line(f"\nWould prune {pruned_count} of {len(entries)} entries.")
            return 0

        # Actually prune
        self.line("\nPruning unreferenced entries...")
        pruned_count = store.prune_unreferenced()

        self.line(f"\n<info>Pruned {pruned_count} unreferenced entries.</info>")
        self.line(f"Kept {len(entries) - pruned_count} entries that are still referenced.")

        return 0