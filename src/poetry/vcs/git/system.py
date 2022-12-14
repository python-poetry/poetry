from __future__ import annotations

import os
import subprocess

from typing import TYPE_CHECKING

from dulwich.client import find_git_command


if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any


class SystemGit:
    fetched_target_list: list[Path] = []

    @classmethod
    def clone(cls, repository: str, dest: Path) -> str:
        cls._check_parameter(repository)

        return cls.run("clone", "--recurse-submodules", "--", repository, str(dest))

    @classmethod
    def checkout(cls, rev: str, target: Path | None = None) -> str:
        args = []

        if target:
            args += cls._construct_dir_args(target)

        cls._check_parameter(rev)

        args += ["checkout", rev]

        return cls.run(*args)

    @classmethod
    def reset(cls, rev: str, target: Path, hard: bool = False) -> str:
        args = cls._construct_dir_args(target)

        cls._check_parameter(rev)

        if hard:
            args += ["reset", "--hard", rev]
        else:
            args += ["reset", rev]

        return cls.run(*args)

    @classmethod
    def fetch(cls, target: Path) -> str | None:
        # fetch once for dependencies from same repo.
        if target in cls.fetched_target_list:
            return None

        args = cls._construct_dir_args(target)
        args += ["fetch"]

        result = cls.run(*args)
        cls.fetched_target_list.append(target)
        return result

    @classmethod
    def run(cls, *args: Any, **kwargs: Any) -> str:
        folder = kwargs.pop("folder", None)
        arg_list = list(args)
        if folder:
            arg_list += cls._construct_dir_args(folder)

        git_command = find_git_command()
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        return (
            subprocess.check_output(
                git_command + arg_list,
                stderr=subprocess.STDOUT,
                env=env,
            )
            .decode()
            .strip()
        )

    @staticmethod
    def _construct_dir_args(target: Path) -> list[str]:
        return [
            "--git-dir",
            (target / ".git").as_posix(),
            "--work-tree",
            target.as_posix(),
        ]

    @staticmethod
    def _check_parameter(parameter: str) -> None:
        """
        Checks a git parameter to avoid unwanted code execution.
        """
        if parameter.strip().startswith("-"):
            raise RuntimeError(f"Invalid Git parameter: {parameter}")
