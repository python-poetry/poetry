import os
import sys

from pathlib import Path
from typing import Union

from poetry.exceptions import PoetryException
from poetry.utils.env import Env
from poetry.utils.env import EnvCommandError
from poetry.utils.env import ephemeral_environment


def pip_install(
    path: Union[Path, str],
    environment: Env,
    editable: bool = False,
    deps: bool = False,
    upgrade: bool = False,
) -> Union[int, str]:
    path = Path(path) if isinstance(path, str) else path
    is_wheel = path.suffix == ".whl"

    # We disable version check here as we are already pinning to version available in either the
    # virtual environment or the virtualenv package embedded wheel. Version checks are a wasteful
    # network call that adds a lot of wait time when installing a lot of packages.
    args = ["install", "--disable-pip-version-check", "--prefix", str(environment.path)]

    if not is_wheel:
        args.insert(1, "--use-pep517")

    if upgrade:
        args.append("--upgrade")

    if not deps:
        args.append("--no-deps")

    if editable:
        if not path.is_dir():
            raise PoetryException(
                "Cannot install non directory dependencies in editable mode"
            )
        args.append("-e")

    args.append(str(path))

    try:
        return environment.run_pip(*args)
    except EnvCommandError as e:
        if sys.version_info < (3, 7) and not is_wheel:
            # Under certain Python3.6 installs vendored pip wheel does not contain zip-safe
            # pep517 lib. In this cases we create an isolated ephemeral virtual environment.
            with ephemeral_environment(
                executable=environment.python, with_pip=True, with_setuptools=True
            ) as env:
                return environment.run(
                    *env.get_pip_command(),
                    *args,
                    env={**os.environ, "PYTHONPATH": str(env.purelib)},
                )
        raise PoetryException(f"Failed to install {path.as_posix()}") from e


def pip_editable_install(directory: Path, environment: Env) -> Union[int, str]:
    return pip_install(
        path=directory, environment=environment, editable=True, deps=False, upgrade=True
    )
