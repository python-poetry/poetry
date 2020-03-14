import atexit
import shutil

from tempfile import mkdtemp

from poetry.utils._compat import Path


def force_rm(action, name, exc):
    Path(name).unlink()


@atexit.register
def cleanup_caches():
    for source, cache in DownloadCache.cache_dirs.items():
        shutil.rmtree(cache, onerror=force_rm)


class DownloadCache:
    cache_dirs = {}

    @classmethod
    def mkcache(cls, source, suffix="", prefix="", dir=""):
        if source not in cls.cache_dirs:
            cls.cache_dirs[source] = mkdtemp(suffix, prefix, dir)

        return cls.cache_dirs[source]
