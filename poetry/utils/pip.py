from pathlib import Path
from typing import Union

from poetry.exceptions import PoetryException
from poetry.utils.env import Env
from poetry.utils.env import ephemeral_environment


def pip_install(
    path: Union[Path, str],
    environment: Env,
    editable: bool = False,
    deps: bool = False,
    upgrade: bool = False,
) -> Union[int, str]:
    path = Path(path) if isinstance(path, str) else path

    args = ["install", "--prefix", str(environment.path)]

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

    if path.is_file() and path.suffix == ".whl":
        return environment.run_pip(*args)

    with ephemeral_environment(
        executable=environment.python, pip=True, setuptools=True
    ) as env:
        return env.run(
            "pip",
            *args,
        )


def pip_editable_install(directory: Path, environment: Env) -> Union[int, str]:
    return pip_install(
        path=directory, environment=environment, editable=True, deps=False, upgrade=True
    )
