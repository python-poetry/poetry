from __future__ import annotations

import os
import re
import shutil
import stat
import tempfile

from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from typing import Iterator


if TYPE_CHECKING:
    from poetry.core.packages.package import Package
    from requests import Session

    from poetry.config.config import Config


_canonicalize_regex = re.compile("[-_]+")


def canonicalize_name(name: str) -> str:
    return _canonicalize_regex.sub("-", name).lower()


def module_name(name: str) -> str:
    return canonicalize_name(name).replace(".", "_").replace("-", "_")


def _del_ro(action: Callable, name: str, exc: Exception) -> None:
    os.chmod(name, stat.S_IWRITE)
    os.remove(name)


@contextmanager
def temporary_directory(*args: Any, **kwargs: Any) -> Iterator[str]:
    name = tempfile.mkdtemp(*args, **kwargs)

    yield name

    shutil.rmtree(name, onerror=_del_ro)


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


def safe_rmtree(path: str) -> None:
    if Path(path).is_symlink():
        return os.unlink(str(path))

    shutil.rmtree(path, onerror=_on_rm_error)


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

    from poetry.puzzle.provider import Indicator

    get = requests.get if not session else session.get

    response = get(url, stream=True)
    response.raise_for_status()

    set_indicator = False
    if "Content-Length" in response.headers:
        try:
            total_size = int(response.headers["Content-Length"])
        except ValueError:
            total_size = 0

        fetched_size = 0
        last_percent = 0

        Indicator.set_context(f"Downloading {url}")
        # if less than 1MB, we simply show that we're downloading but skip the updating
        set_indicator = total_size > 1024 * 1024

    with open(dest, "wb") as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)

                if set_indicator:
                    fetched_size += len(chunk)
                    percent = (fetched_size * 100) // total_size
                    if percent > last_percent:
                        last_percent = percent
                        Indicator.set_context(f"Downloading {url} {percent:3}%")

    Indicator.set_context(None)


def get_package_version_display_string(
    package: Package, root: Path | None = None
) -> str:
    if package.source_type in ["file", "directory"] and root:
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
