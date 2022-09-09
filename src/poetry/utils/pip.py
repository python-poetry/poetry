from __future__ import annotations

import itertools
import os
import tempfile

from typing import TYPE_CHECKING
from typing import Any
from typing import Collection

from poetry.core.semver.version import Version

from poetry.exceptions import PoetryException
from poetry.utils.env import EnvCommandError
from poetry.utils.env import EnvManager


if TYPE_CHECKING:
    from pathlib import Path

    from poetry.utils.env import Env


class Pip:
    def __init__(self, target_env: Env | None) -> None:
        self._poetry_env = EnvManager.get_system_env(naive=True)

        if not target_env:
            target_env = self._poetry_env

        self._target_env = target_env

    def run(self, *args: str, **kwargs: Any) -> int | str:
        return self._poetry_env.run(
            "python", "-m", "pip", "--disable-pip-version-check", *args, **kwargs
        )

    def _install(self, *args: str) -> int | str:
        platform_args = itertools.chain.from_iterable(
            ["--platform", platform]
            for platform in {tag.platform for tag in self._target_env.supported_tags}
        )
        abi_args = itertools.chain.from_iterable(
            ["--abi", abi]
            for abi in {tag.abi for tag in self._target_env.supported_tags}
        )

        run_result = self.run(
            "install",
            "--no-warn-script-location",
            "--target",
            str(self._target_env.platlib),
            "--implementation",
            self._target_env.marker_env["interpreter_name"],
            "--python-version",
            self._target_env.marker_env["python_version"],
            *platform_args,
            *abi_args,
            *args,
        )

        return run_result

    def install_archive(
        self,
        path: Path,
        editable: bool = False,
        deps: bool = False,
        upgrade: bool = False,
    ) -> int | str:
        args = []

        if path.suffix != ".whl" and not editable:
            args.append("--use-pep517")

        if upgrade:
            args.append("--upgrade")

        if not deps:
            args.append("--no-deps")

        if editable:
            if not path.is_dir():
                raise PoetryException(
                    "Only directory dependencies can be installed in editable mode"
                )
            args.append("-e")

        args.append(str(path))

        try:
            return self._install(*args)
        except EnvCommandError as e:
            raise PoetryException(f"Failed to install {path.as_posix()}") from e

    def install_requirements(self, requirements: Collection[str]) -> int | str:
        with tempfile.NamedTemporaryFile(
            "w+", prefix="requirements-", suffix=".txt"
        ) as requirements_txt:
            requirements_txt.write(os.linesep.join(requirements))
            try:
                return self._install(
                    "--use-pep517", "-r", os.path.abspath(requirements_txt.name)
                )
            except EnvCommandError as e:
                raise PoetryException(
                    f"Failed to install requirements {', '.join(requirements)}"
                ) from e

    @staticmethod
    def version() -> Version:
        from pip import __version__

        return Version.parse(__version__)
