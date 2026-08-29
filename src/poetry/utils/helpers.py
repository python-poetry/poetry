from __future__ import annotations

import copy
import hashlib
import io
import logging
import os
import shutil
import stat
import sys
import tarfile
import tempfile
import warnings
import zipfile

from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import overload


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Collection
    from collections.abc import Iterator
    from types import TracebackType

    from poetry.core.packages.package import Package


logger = logging.getLogger(__name__)
prioritised_hash_types: tuple[str, ...] = tuple(
    t
    for t in [
        "sha3_512",
        "sha3_384",
        "sha3_256",
        "sha3_224",
        "sha512",
        "sha384",
        "sha256",
        "sha224",
        "shake_256",
        "shake_128",
        "blake2s",
        "blake2b",
    ]
    if t in hashlib.algorithms_available
)
non_prioritised_available_hash_types: frozenset[str] = frozenset(
    set(hashlib.algorithms_available).difference(prioritised_hash_types)
)


@contextmanager
def directory(path: Path) -> Iterator[Path]:
    cwd = Path.cwd()
    try:
        os.chdir(path)
        yield path
    finally:
        os.chdir(cwd)


# Correct type signature when used as `shutil.rmtree(..., onexc=_on_rm_error)`.
@overload
def _on_rm_error(
    func: Callable[[str], None], path: str, exc_info: Exception
) -> None: ...


# Correct type signature when used as `shutil.rmtree(..., onerror=_on_rm_error)`.
@overload
def _on_rm_error(
    func: Callable[[str], None],
    path: str,
    exc_info: tuple[type[BaseException], BaseException, TracebackType],
) -> None: ...


def _on_rm_error(func: Callable[[str], None], path: str, exc_info: Any) -> None:
    if not os.path.exists(path):
        return

    os.chmod(path, stat.S_IWRITE)
    func(path)


def remove_directory(path: Path, force: bool = False) -> None:
    """
    Helper function handle safe removal, and optionally forces stubborn file removal.
    This is particularly useful when dist files are read-only or git writes read-only
    files on Windows.

    Internally, all arguments are passed to `shutil.rmtree`.
    """
    if path.is_symlink():
        return os.unlink(path)

    kwargs: dict[str, Any] = {}
    if force:
        onexc = "onexc" if sys.version_info >= (3, 12) else "onerror"
        kwargs[onexc] = _on_rm_error

    shutil.rmtree(path, **kwargs)


def merge_dicts(d1: dict[str, Any], d2: dict[str, Any]) -> None:
    for k in d2:
        if k in d1 and isinstance(d1[k], dict) and isinstance(d2[k], Mapping):
            merge_dicts(d1[k], d2[k])
        else:
            d1[k] = d2[k]


def get_package_version_display_string(
    package: Package, root: Path | None = None
) -> str:
    if package.source_type in ["file", "directory"] and root:
        assert package.source_url is not None
        path = Path(os.path.relpath(package.source_url, root)).as_posix()
        return f"{package.version} {path}"

    pretty_version: str = package.full_pretty_version
    return pretty_version


def paths_csv(paths: list[Path]) -> str:
    return ", ".join(f'"{c!s}"' for c in paths)


def ensure_path(path: str | Path, is_directory: bool = False) -> Path:
    if isinstance(path, str):
        path = Path(path)

    if path.exists() and path.is_dir() == is_directory:
        return path

    raise ValueError(
        f"Specified path '{path}' is not a valid {'directory' if is_directory else 'file'}."
    )


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


def _get_win_folder_from_registry(csidl_name: str) -> str:
    if sys.platform != "win32":
        raise RuntimeError("Method can only be called on Windows.")

    import winreg as _winreg

    shell_folder_name = {
        "CSIDL_APPDATA": "AppData",
        "CSIDL_COMMON_APPDATA": "Common AppData",
        "CSIDL_LOCAL_APPDATA": "Local AppData",
        "CSIDL_PROGRAM_FILES": "Program Files",
    }[csidl_name]

    key = _winreg.OpenKey(
        _winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
    )
    dir, _type = _winreg.QueryValueEx(key, shell_folder_name)

    assert isinstance(dir, str)
    return dir


def _get_win_folder_with_ctypes(csidl_name: str) -> str:
    if sys.platform != "win32":
        raise RuntimeError("Method can only be called on Windows.")

    import ctypes

    csidl_const = {
        "CSIDL_APPDATA": 26,
        "CSIDL_COMMON_APPDATA": 35,
        "CSIDL_LOCAL_APPDATA": 28,
        "CSIDL_PROGRAM_FILES": 38,
    }[csidl_name]

    buf = ctypes.create_unicode_buffer(1024)
    ctypes.windll.shell32.SHGetFolderPathW(None, csidl_const, None, 0, buf)

    # Downgrade to short path name if have highbit chars. See
    # <http://bugs.activestate.com/show_bug.cgi?id=85099>.
    has_high_char = False
    for c in buf:
        if ord(c) > 255:
            has_high_char = True
            break
    if has_high_char:
        buf2 = ctypes.create_unicode_buffer(1024)
        if ctypes.windll.kernel32.GetShortPathNameW(buf.value, buf2, 1024):
            buf = buf2

    return buf.value


def get_win_folder(csidl_name: str) -> Path:
    if sys.platform == "win32":
        try:
            from ctypes import windll  # noqa: F401

            _get_win_folder = _get_win_folder_with_ctypes
        except ImportError:
            _get_win_folder = _get_win_folder_from_registry

        return Path(_get_win_folder(csidl_name))

    raise RuntimeError("Method can only be called on Windows.")


def get_real_windows_path(path: Path) -> Path:
    program_files = get_win_folder("CSIDL_PROGRAM_FILES")
    local_appdata = get_win_folder("CSIDL_LOCAL_APPDATA")

    path = Path(
        str(path).replace(
            str(program_files / "WindowsApps"),
            str(local_appdata / "Microsoft/WindowsApps"),
        )
    )

    if path.as_posix().startswith(local_appdata.as_posix()):
        path = path.resolve()

    return path


def get_file_hash(path: Path, hash_name: str = "sha256") -> str:
    h = hashlib.new(hash_name)
    with path.open("rb") as fp:
        for content in iter(lambda: fp.read(io.DEFAULT_BUFFER_SIZE), b""):
            h.update(content)

    return h.hexdigest()


def get_highest_priority_hash_type(
    hash_types: Collection[str], archive_name: str
) -> str | None:
    if not hash_types:
        return None

    for prioritised_hash_type in prioritised_hash_types:
        if prioritised_hash_type in hash_types:
            return prioritised_hash_type

    logger.debug(
        f"There are no known hash types for {archive_name} that are prioritised (known"
        f" hash types: {hash_types!s})"
    )

    for available_hash_type in non_prioritised_available_hash_types:
        if available_hash_type in hash_types:
            return available_hash_type

    return None


def extractall(source: Path, dest: Path, zip: bool) -> None:
    """Extract all members from either a zip or tar archive."""
    if zip:
        with zipfile.ZipFile(source) as zip_archive:
            zip_archive.extractall(dest)
    else:
        # These versions of python shipped with a broken tarfile data_filter, per
        # https://github.com/python/cpython/issues/107845.
        broken_tarfile_filter = {(3, 10, 12), (3, 11, 4)}
        with tarfile.open(source) as archive:
            if (
                hasattr(tarfile, "data_filter")
                and sys.version_info[:3] not in broken_tarfile_filter
            ):
                archive.extractall(dest, filter="data")
            else:

                def _get_filtered_attrs(
                    member: tarfile.TarInfo, dest_path: str
                ) -> dict[str, Any]:
                    """copied from CPython 3.14.7 with slight adaptions:
                    - removed parameter for_data (always True in this case)
                    - replaced exceptions with ValueError
                    - removed ALLOW_MISSING
                    - added some type hints to make mypy happy
                    """
                    new_attrs: dict[str, Any] = {}
                    name = member.name
                    dest_path = os.path.realpath(
                        dest_path,
                    )
                    # Strip leading / (tar's directory separator) from filenames.
                    # Include os.sep (target OS directory separator) as well.
                    if name.startswith(("/", os.sep)):
                        name = new_attrs["name"] = member.path.lstrip("/" + os.sep)
                    if os.path.isabs(name):
                        # Path is absolute even after stripping.
                        # For example, 'C:/foo' on Windows.
                        raise ValueError(
                            f"Refusing to extract {member.name}: absolute path"
                        )
                    # Ensure we stay in the destination
                    target_path = os.path.realpath(os.path.join(dest_path, name))
                    if os.path.commonpath([target_path, dest_path]) != dest_path:
                        raise ValueError(
                            f"Refusing to extract {member.name}: would write outside {dest_path}"
                        )
                    # Limit permissions (no high bits, and go-w)
                    mode: int | None = member.mode
                    if mode is not None:
                        # Strip high bits & group/other write bits
                        mode = mode & 0o755
                        # For data, handle permissions & file types
                        if member.isreg() or member.islnk():
                            if not mode & 0o100:
                                # Clear executable bits if not executable by user
                                mode &= ~0o111
                            # Ensure owner can read & write
                            mode |= 0o600
                        elif member.isdir() or member.issym():
                            # Ignore mode for directories & symlinks
                            mode = None
                        else:
                            # Reject special files
                            raise ValueError(
                                f"Refusing to extract special file {member.name}"
                            )
                        if mode != member.mode:
                            new_attrs["mode"] = mode
                    # Ignore ownership for 'data'
                    if member.uid is not None:
                        new_attrs["uid"] = None
                    if member.gid is not None:
                        new_attrs["gid"] = None
                    if member.uname is not None:
                        new_attrs["uname"] = None
                    if member.gname is not None:
                        new_attrs["gname"] = None
                    # Check link destination for 'data'
                    if member.islnk() or member.issym():
                        if os.path.isabs(member.linkname):
                            raise ValueError(
                                f"Refusing to extract {member.name}: link has an absolute target"
                            )
                        # A link member that resolves to the destination directory itself
                        # would replace it with a (sym)link, redirecting the destination
                        # for all subsequent members.
                        if target_path == dest_path:
                            raise ValueError(
                                f"Refusing to extract {member.name}: "
                                "link target is the destination directory"
                            )
                        normalized = os.path.normpath(member.linkname)
                        if normalized != member.linkname:
                            new_attrs["linkname"] = normalized
                        if member.issym():
                            # The symlink is created at `name` with trailing separators
                            # stripped, so its target is relative to the directory
                            # containing that path.
                            link_dir = os.path.dirname(name.rstrip("/" + os.sep))
                            target_path = os.path.join(dest_path, link_dir, normalized)
                        else:
                            target_path = os.path.join(dest_path, normalized)
                        target_path = os.path.realpath(target_path)
                        if os.path.commonpath([target_path, dest_path]) != dest_path:
                            raise ValueError(
                                f"Refusing to extract {member.name}: "
                                f"link target {member.linkname} outside {dest_path}"
                            )
                    return new_attrs

                dest = Path(os.path.abspath(dest))
                for member in archive.getmembers():
                    new_attrs = _get_filtered_attrs(member, str(dest))
                    if new_attrs:
                        member = copy.copy(member)
                        for name, value in new_attrs.items():
                            setattr(member, name, value)
                    archive.extract(member, dest, set_attrs=not member.isdir())


_DEPRECATED_DOWNLOAD_EXPORTS = {
    "Downloader",
    "download_file",
    "HTTPRangeRequestSupportedError",
}


def __getattr__(name: str) -> object:
    if name in _DEPRECATED_DOWNLOAD_EXPORTS:
        warnings.warn(
            f"Importing `{name}` from `poetry.utils.helpers` is deprecated;"
            f" use `poetry.utils.download.{name}` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from poetry.utils import download

        return getattr(download, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
