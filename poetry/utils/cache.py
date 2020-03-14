from tempfile import TemporaryDirectory


class DownloadCache:
    cache_dirs = {}

    @classmethod
    def mkcache(cls, source=None, suffix=None, prefix=None, dir=None):
        if source not in cls.cache_dirs:
            cls.cache_dirs[source] = TemporaryDirectory(suffix, prefix, dir)

        return cls.cache_dirs[source].name
