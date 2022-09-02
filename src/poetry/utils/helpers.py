import os
import re
import shutil
import stat
import tempfile
import time

from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional


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

    robust_rmtree(name, onerror=_del_ro)


def get_cert(config: "Config", repository_name: str) -> Optional[Path]:
    cert = config.get(f"certificates.{repository_name}.cert")
    if cert:
        return Path(cert)
    else:
        return None


def get_client_cert(config: "Config", repository_name: str) -> Optional[Path]:
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


def robust_rmtree(path: str, onerror: Callable = None, max_timeout: float = 1) -> None:
    """
    Robustly tries to delete paths.
    Retries several times if an OSError occurs.
    If the final attempt fails, the Exception is propagated
    to the caller.
    """
    timeout = 0.001
    while timeout < max_timeout:
        try:
            shutil.rmtree(path)
            return  # Only hits this on success
        except OSError:
            # Increase the timeout and try again
            time.sleep(timeout)
            timeout *= 2

    # Final attempt, pass any Exceptions up to caller.
    shutil.rmtree(path, onerror=onerror)


def safe_rmtree(path: str) -> None:
    if Path(path).is_symlink():
        return os.unlink(str(path))

    shutil.rmtree(
        path, onerror=_on_rm_error
    )  # maybe we could call robust_rmtree here just in case ?


def merge_dicts(d1: Dict, d2: Dict) -> None:
    for k in d2.keys():
        if k in d1 and isinstance(d1[k], dict) and isinstance(d2[k], Mapping):
            merge_dicts(d1[k], d2[k])
        else:
            d1[k] = d2[k]


def download_file(
    url: str,
    dest: str,
    session: Optional["Session"] = None,
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
    package: "Package", root: Optional[Path] = None
) -> str:
    if package.source_type in ["file", "directory"] and root:
        path = Path(os.path.relpath(package.source_url, root.as_posix())).as_posix()
        return f"{package.version} {path}"

    return package.full_pretty_version


def paths_csv(paths: List[Path]) -> str:
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
