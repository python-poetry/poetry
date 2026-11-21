from __future__ import annotations

from poetry.config.config import Config
from poetry.console.commands.cache.clear import ARTIFACTS_CACHE_NAME
from poetry.console.commands.command import Command


class CacheListCommand(Command):
    name = "cache list"
    description = "List Poetry's caches."

    def handle(self) -> int:
        config = Config.create()
        caches: list[str] = []

        if config.repository_cache_directory.exists():
            caches.extend(
                sorted(
                    cache.name for cache in config.repository_cache_directory.iterdir()
                )
            )

        if config.artifacts_cache_directory.exists():
            caches.append(ARTIFACTS_CACHE_NAME)

        if caches:
            for cache in caches:
                self.line(f"<info>{cache}</>")
            return 0

        self.line_error("<warning>No caches found</>")
        return 0
