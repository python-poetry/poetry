from __future__ import annotations

import functools
import json
import os
import platform
import sys

from typing import Any

from poetry.__version__ import __version__


@functools.cache
def get_user_agent() -> str:
    """
    Return a user agent containing environment data for PyPI's linehaul.

    The format mirrors pip's: the installer name and version followed by a JSON
    object, see https://github.com/pypi/linehaul-cloud-function.
    """
    data: dict[str, Any] = {
        "installer": {"name": "poetry", "version": __version__},
        "python": platform.python_version(),
        "implementation": {
            "name": platform.python_implementation(),
            "version": platform.python_version(),
        },
    }

    if data["implementation"]["name"] == "PyPy":
        pypy_version_info = sys.pypy_version_info  # type: ignore[attr-defined]
        if pypy_version_info.releaselevel == "final":
            pypy_version_info = pypy_version_info[:3]
        data["implementation"]["version"] = ".".join(
            str(part) for part in pypy_version_info
        )

    if sys.platform.startswith("linux"):
        distro: dict[str, Any] = {}
        try:
            os_release = platform.freedesktop_os_release()
        except OSError:
            pass
        else:
            distro.update(
                (key, os_release[field])
                for key, field in (
                    ("name", "NAME"),
                    ("version", "VERSION_ID"),
                    ("id", "VERSION_CODENAME"),
                )
                if os_release.get(field)
            )

        try:
            libc_version = os.confstr("CS_GNU_LIBC_VERSION")
        except (AttributeError, ValueError, OSError):
            pass
        else:
            if libc_version and len(parts := libc_version.split()) == 2:
                distro["libc"] = {"lib": parts[0], "version": parts[1]}

        if distro:
            data["distro"] = distro

    if sys.platform.startswith("darwin") and (mac_version := platform.mac_ver()[0]):
        data["distro"] = {"name": "macOS", "version": mac_version}

    if system := platform.system():
        data.setdefault("system", {})["name"] = system
    if release := platform.release():
        data.setdefault("system", {})["release"] = release
    if machine := platform.machine():
        data["cpu"] = machine

    try:
        import ssl
    except ImportError:
        pass
    else:
        data["openssl_version"] = ssl.OPENSSL_VERSION

    # Omit setuptools_version (Poetry's own environment) and rustc_version
    # (requires a subprocess), which are not meaningful or cheap for Poetry.

    # Use None rather than False so as not to give the impression that
    # Poetry knows it is not being run under CI. Rather, it is a null or
    # inconclusive result. Also, we include some value rather than no
    # value to make it easier to know that the check has been run.
    data["ci"] = (
        True
        if any(name in os.environ for name in ("BUILD_BUILDID", "BUILD_ID", "CI"))
        else None
    )

    payload = json.dumps(data, separators=(",", ":"), sort_keys=True)

    return f"poetry/{__version__} {payload}"
