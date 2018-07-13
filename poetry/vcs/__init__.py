import subprocess
import warnings

from poetry.utils._compat import Path

from .git import Git


def get_vcs(directory):  # type: (Path) -> Git
    directory = directory.resolve()

    for p in [directory] + list(directory.parents):
        if (p / ".git").is_dir():
            try:
                return Git(p)
            except (subprocess.CalledProcessError, OSError):
                # Either git could not be found or does not exist
                warnings.warn(
                    "git executable could not be found", category=RuntimeWarning
                )

                return
