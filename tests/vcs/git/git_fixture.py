from __future__ import annotations

import typing


if typing.TYPE_CHECKING:
    from pathlib import Path

    import dulwich.repo


class TempRepoFixture(typing.NamedTuple):
    path: Path
    repo: dulwich.repo.Repo
    init_commit: str
    middle_commit: str
    head_commit: str
