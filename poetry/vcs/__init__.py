from poetry.utils._compat import Path

from .git import Git


def get_vcs(directory):  # type: (Path) -> Git
    directory = directory.resolve()

    for p in [directory] + list(directory.parents):
        if (p / '.git').is_dir():
            return Git(p)
