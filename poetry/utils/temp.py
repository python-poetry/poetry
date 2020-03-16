import atexit
import shutil

from tempfile import mkdtemp

from poetry.utils._compat import Path


def force_rm(action, name, exc):
    Path(name).unlink()


@atexit.register
def cleanup_tmp():
    for source, cache in DownloadTmpDir.tmp_dirs.items():
        shutil.rmtree(cache, onerror=force_rm)


class DownloadTmpDir:
    tmp_dirs = {}

    @classmethod
    def mkcache(cls, source, suffix="", prefix="", dir=""):
        if source not in cls.tmp_dirs:
            cls.tmp_dirs[source] = mkdtemp(suffix, prefix, dir)

        return cls.tmp_dirs[source]
