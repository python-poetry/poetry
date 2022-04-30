from __future__ import annotations

import os
import re
import shutil
import stat
import tempfile

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Callable


if TYPE_CHECKING:
    from poetry.core.packages.package import Package
    from requests import Session

    from poetry.config.config import Config


_canonicalize_regex = re.compile("[-_]+")


def canonicalize_name(name: str) -> str:
    return _canonicalize_regex.sub("-", name).lower()


def module_name(name: str) -> str:
    return canonicalize_name(name).replace(".", "_").replace("-", "_")


def get_cert(config: Config, repository_name: str) -> Path | None:
    cert = config.get(f"certificates.{repository_name}.cert")
    if cert:
        return Path(cert)
    else:
        return None


def get_client_cert(config: Config, repository_name: str) -> Path | None:
    client_cert = config.get(f"certificates.{repository_name}.client-cert")
    if client_cert:
        return Path(client_cert)
    else:
        return None


def _on_rm_error(func: Callable, path: str, exc_info: Exception) -> None:
    if not os.path.exists(path):
        return

    os.chmod(path, stat.S_IWRITE)
    func(path)


def remove_directory(
    path: Path | str, *args: Any, force: bool = False, **kwargs: Any
) -> None:
    """
    Helper function handle safe removal, and optionally forces stubborn file removal.
    This is particularly useful when dist files are read-only or git writes read-only
    files on Windows.

    Internally, all arguments are passed to `shutil.rmtree`.
    """
    if Path(path).is_symlink():
        return os.unlink(str(path))

    kwargs["onerror"] = kwargs.pop("onerror", _on_rm_error if force else None)
    shutil.rmtree(path, *args, **kwargs)


def merge_dicts(d1: dict, d2: dict) -> None:
    for k in d2.keys():
        if k in d1 and isinstance(d1[k], dict) and isinstance(d2[k], Mapping):
            merge_dicts(d1[k], d2[k])
        else:
            d1[k] = d2[k]


def download_file(
    url: str,
    dest: str,
    session: Session | None = None,
    chunk_size: int = 1024,
) -> None:
    import requests

    get = requests.get if not session else session.get

    response = get(url, stream=True)
    response.raise_for_status()

    with open(dest, "wb") as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)


def get_package_version_display_string(
    package: Package, root: Path | None = None
) -> str:
    if package.source_type in ["file", "directory"] and root:
        assert package.source_url is not None
        path = Path(os.path.relpath(package.source_url, root.as_posix())).as_posix()
        return f"{package.version} {path}"

    return package.full_pretty_version


def paths_csv(paths: list[Path]) -> str:
    return ", ".join(f'"{c!s}"' for c in paths)


def is_dir_writable(path: Path, create: bool = False) -> bool:
    try:
        if not path.exists():
            if not create:
                return False
            path.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryFile(dir=str(path)):
            pass
    except OSError:
        return False
    else:
        return True


def pluralize(count: int, word: str = "") -> str:
    if count == 1:
        return word
    return word + "s"
