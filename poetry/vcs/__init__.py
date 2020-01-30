import os
import subprocess

from poetry.utils._compat import Path
from poetry.utils._compat import decode

from .git import Git


def get_vcs(directory):  # type: (Path) -> Git
    os.chdir(str(directory))

    try:
        git_dir = decode(
            subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"], stderr=subprocess.STDOUT
            )
        ).strip()

        return Git(Path(git_dir))

    except subprocess.CalledProcessError:

        return
