from __future__ import annotations

from typing import TYPE_CHECKING

from poetry import __version__
from poetry.exceptions import PoetryException
from poetry.utils.env import EnvCommandError


if TYPE_CHECKING:
    from pathlib import Path

    from poetry.utils.env import Env


from installer import install
from installer.destinations import SchemeDictionaryDestination
from installer.sources import WheelFile


def wheel_install(path: Path, environment: Env) -> int:
    if path.suffix != ".whl":
        raise PoetryException(f"{path.as_posix()} is not a wheel")

    destination = SchemeDictionaryDestination(
        environment.paths,
        interpreter=environment.python,
        # TODO: ensure platform specific values here
        script_kind="posix",
    )

    with WheelFile.open(path) as source:
        install(
            source=source,
            destination=destination,
            additional_metadata={
                "INSTALLER": f"poetry {__version__}".encode(),
            },
        )

    return 0


def pip_install(
    path: Path,
    environment: Env,
    editable: bool = False,
    deps: bool = False,
    upgrade: bool = False,
) -> int | str:
    is_wheel = path.suffix == ".whl"

    if is_wheel:
        return wheel_install(path, environment)

    # We disable version check here as we are already pinning to version available in
    # either the virtual environment or the virtualenv package embedded wheel. Version
    # checks are a wasteful network call that adds a lot of wait time when installing a
    # lot of packages.
    args = [
        "install",
        "--disable-pip-version-check",
        "--isolated",
        "--no-input",
        "--prefix",
        str(environment.path),
    ]

    if not editable:
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
        raise PoetryException(f"Failed to install {path.as_posix()}") from e
