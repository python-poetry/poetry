import os

from typing import Optional

from ..command import Command


class CacheListCommand(Command):

    name = "cache list"
    description = "List Poetry's caches."

    def handle(self) -> Optional[int]:
        from poetry.locations import REPOSITORY_CACHE_DIR

        if os.path.exists(str(REPOSITORY_CACHE_DIR)):
            caches = list(sorted(REPOSITORY_CACHE_DIR.iterdir()))
            if caches:
                for cache in caches:
                    self.line("<info>{}</>".format(cache.name))
                return 0

        self.line("<warning>No caches found</>")
