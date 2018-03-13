from pathlib import Path

from .git import Git


def get_vcs(directory: Path):
    directory = directory.resolve()

    for p in [directory] + list(directory.parents):
        if (p / '.git').is_dir():
            return Git(p)
