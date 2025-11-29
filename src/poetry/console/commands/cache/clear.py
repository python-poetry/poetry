from __future__ import annotations

import os

from typing import TYPE_CHECKING
from typing import ClassVar

from cleo.helpers import argument
from cleo.helpers import option
from packaging.utils import canonicalize_name

from poetry.config.config import Config
from poetry.console.commands.command import Command
from poetry.utils.cache import FileCache


if TYPE_CHECKING:
    from cleo.io.inputs.argument import Argument
    from cleo.io.inputs.option import Option


class CacheClearCommand(Command):
    name = "cache clear"
    description = "Clear Poetry's caches."

    arguments: ClassVar[list[Argument]] = [
        argument("cache", description="The name of the cache to clear.", optional=True)
    ]
    options: ClassVar[list[Option]] = [
        option("all", description="Clear all entries in the cache.")
    ]

    def handle(self) -> int:
        cache = self.argument("cache")

        if cache:
            parts = cache.split(":")
            root = parts[0]
        else:
            parts = []
            root = ""

        config = Config.create()
        cache_dir = config.repository_cache_directory / root

        try:
            cache_dir.relative_to(config.repository_cache_directory)
        except ValueError:
            raise ValueError(f"{root} is not a valid repository cache")

        cache = FileCache(cache_dir)

        if len(parts) < 2:
            if not self.option("all"):
                raise RuntimeError(
                    "Add the --all option if you want to clear all cache entries"
                )

            if not cache_dir.exists():
                self.line(
                    f"No cache entries for {root}" if root else "No cache entries"
                )
                return 0

            # Calculate number of entries
            entries_count = sum(
                len(files) for _path, _dirs, files in os.walk(str(cache_dir))
            )

            delete = self.confirm(f"<question>Delete {entries_count} entries?</>", True)
            if not delete:
                return 0

            cache.flush()
        elif len(parts) == 2:
            raise RuntimeError(
                "Only specifying the package name is not yet supported. "
                "Add a specific version to clear"
            )
        elif len(parts) == 3:
            package = canonicalize_name(parts[1])
            version = parts[2]

            if not cache.has(f"{package}:{version}"):
                self.line(f"No cache entries for {package}:{version}")
                return 0

            delete = self.confirm(f"Delete cache entry {package}:{version}", True)
            if not delete:
                return 0

            cache.forget(f"{package}:{version}")
        else:
            raise ValueError("Invalid cache key")

        return 0
