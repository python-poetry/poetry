import os

from cleo.helpers import argument
from cleo.helpers import option

from poetry.console.commands.command import Command


class CacheClearCommand(Command):

    name = "cache clear"
    description = "Clears Poetry's cache."

    arguments = [argument("cache", description="The name of the cache to clear.")]
    options = [option("all", description="Clear all entries in the cache.")]

    def handle(self) -> int:
        from cachy import CacheManager

        from poetry.locations import REPOSITORY_CACHE_DIR

        cache = self.argument("cache")

        parts = cache.split(":")
        root = parts[0]

        cache_dir = REPOSITORY_CACHE_DIR / root

        try:
            cache_dir.relative_to(REPOSITORY_CACHE_DIR)
        except ValueError:
            raise ValueError(f"{root} is not a valid repository cache")

        cache = CacheManager(
            {
                "default": parts[0],
                "serializer": "json",
                "stores": {parts[0]: {"driver": "file", "path": str(cache_dir)}},
            }
        )

        if len(parts) == 1:
            if not self.option("all"):
                raise RuntimeError(
                    "Add the --all option if you want to clear all "
                    f"{parts[0]} caches"
                )

            if not os.path.exists(str(cache_dir)):
                self.line(f"No cache entries for {parts[0]}")
                return 0

            # Calculate number of entries
            entries_count = 0
            for _path, _dirs, files in os.walk(str(cache_dir)):
                entries_count += len(files)

            delete = self.confirm(f"<question>Delete {entries_count} entries?</>")
            if not delete:
                return 0

            cache.flush()
        elif len(parts) == 2:
            raise RuntimeError(
                "Only specifying the package name is not yet supported. "
                "Add a specific version to clear"
            )
        elif len(parts) == 3:
            package = parts[1]
            version = parts[2]

            if not cache.has(f"{package}:{version}"):
                self.line(f"No cache entries for {package}:{version}")
                return 0

            delete = self.confirm(f"Delete cache entry {package}:{version}")
            if not delete:
                return 0

            cache.forget(f"{package}:{version}")
        else:
            raise ValueError("Invalid cache key")
