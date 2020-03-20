import os
import subprocess

from poetry.utils._compat import Path
from poetry.utils._compat import decode

from .git import Git


def get_vcs(directory):  # type: (Path) -> Git
    working_dir = Path.cwd()
    os.chdir(str(directory.resolve()))

    try:
        git_dir = decode(
            subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"], stderr=subprocess.STDOUT
            )
        ).strip()

        vcs = Git(Path(git_dir))

    except (subprocess.CalledProcessError, OSError):
        vcs = None
    finally:
        os.chdir(str(working_dir))

    return vcs
