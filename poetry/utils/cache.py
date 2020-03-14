import atexit
import shutil

from tempfile import mkdtemp


@atexit.register
def cleanup_caches():
    for source, cache in DownloadCache.cache_dirs.items():
        shutil.rmtree(cache)


class DownloadCache:
    cache_dirs = {}

    @classmethod
    def mkcache(cls, source, suffix=None, prefix=None, dir=None):
        if source not in cls.cache_dirs:
            cls.cache_dirs[source] = mkdtemp(suffix, prefix, dir)

        return cls.cache_dirs[source]
