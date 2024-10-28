from __future__ import annotations

import shutil
import typing


if typing.TYPE_CHECKING:
    from pathlib import Path

    import dulwich.repo


GIT_NOT_INSTALLLED = shutil.which("git") is None


class TempRepoFixture(typing.NamedTuple):
    path: Path
    repo: dulwich.repo.Repo
    init_commit: str
    middle_commit: str
    head_commit: str
