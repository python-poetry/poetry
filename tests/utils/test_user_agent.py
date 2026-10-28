from __future__ import annotations

import json
import os
import platform
import ssl
import sys

from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple

import pytest

from poetry.__version__ import __version__
from poetry.utils.user_agent import get_user_agent


if TYPE_CHECKING:
    from collections.abc import Iterator

    from pytest import MonkeyPatch


@pytest.fixture(autouse=True)
def clear_user_agent_cache() -> Iterator[None]:
    get_user_agent.cache_clear()
    yield
    get_user_agent.cache_clear()


@pytest.fixture(autouse=True)
def mock_environment(monkeypatch: MonkeyPatch) -> None:
    for name in ("BUILD_BUILDID", "BUILD_ID", "CI"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(platform, "python_version", lambda: "3.13.5")
    monkeypatch.setattr(platform, "python_implementation", lambda: "CPython")
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(platform, "release", lambda: "10")
    monkeypatch.setattr(platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(ssl, "OPENSSL_VERSION", "OpenSSL 3.0.0")


def _linehaul_data() -> dict[str, Any]:
    # Parse the user agent the same way linehaul parses pip's and uv's.
    data: dict[str, Any] = json.loads(get_user_agent().split(" ", 1)[1])
    return data


def test_user_agent_format() -> None:
    user_agent = get_user_agent()
    prefix, payload = user_agent.split(" ", 1)
    data = json.loads(payload)

    assert prefix == f"poetry/{__version__}"
    assert payload == json.dumps(data, separators=(",", ":"), sort_keys=True)
    assert set(data) <= {
        "installer",
        "python",
        "implementation",
        "distro",
        "system",
        "cpu",
        "openssl_version",
        "setuptools_version",
        "rustc_version",
        "ci",
    }
    assert data["installer"] == {"name": "poetry", "version": __version__}
    assert data["python"] == "3.13.5"
    assert data["implementation"] == {"name": "CPython", "version": "3.13.5"}
    assert data["system"] == {"name": "Windows", "release": "10"}
    assert data["cpu"] == "AMD64"
    assert data["openssl_version"] == "OpenSSL 3.0.0"
    assert data["ci"] is None


@pytest.mark.parametrize("name", ["BUILD_BUILDID", "BUILD_ID", "CI"])
@pytest.mark.parametrize("value", ["true", ""])
def test_user_agent_ci(monkeypatch: MonkeyPatch, name: str, value: str) -> None:
    monkeypatch.setenv(name, value)

    assert _linehaul_data()["ci"] is True


def test_user_agent_linux(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(
        platform,
        "freedesktop_os_release",
        lambda: {
            "NAME": "Ubuntu",
            "VERSION_ID": "24.04",
            "VERSION_CODENAME": "noble",
        },
    )

    def confstr(name: str) -> str:
        assert name == "CS_GNU_LIBC_VERSION"
        return "glibc 2.39"

    monkeypatch.setattr(os, "confstr", confstr, raising=False)

    assert _linehaul_data()["distro"] == {
        "name": "Ubuntu",
        "version": "24.04",
        "id": "noble",
        "libc": {"lib": "glibc", "version": "2.39"},
    }


@pytest.mark.parametrize("error", [AttributeError, ValueError, OSError])
def test_user_agent_linux_without_os_release_or_glibc(
    monkeypatch: MonkeyPatch, error: type[Exception]
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")

    def os_release() -> dict[str, str]:
        raise OSError

    def confstr(name: str) -> str:
        raise error

    monkeypatch.setattr(platform, "freedesktop_os_release", os_release)
    monkeypatch.setattr(os, "confstr", confstr, raising=False)

    assert "distro" not in _linehaul_data()


@pytest.mark.parametrize(
    "os_release,libc,expected",
    [
        ({"NAME": "", "VERSION_ID": "", "VERSION_CODENAME": ""}, None, None),
        ({"NAME": "Ubuntu", "VERSION_ID": ""}, None, {"name": "Ubuntu"}),
        ({}, "glibc 2.39", {"libc": {"lib": "glibc", "version": "2.39"}}),
        ({}, "", None),
        ({}, "glibc", None),
    ],
)
def test_user_agent_linux_optional_values(
    monkeypatch: MonkeyPatch,
    os_release: dict[str, str],
    libc: str | None,
    expected: dict[str, str | dict[str, str]] | None,
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(platform, "freedesktop_os_release", lambda: os_release)
    monkeypatch.setattr(os, "confstr", lambda name: libc, raising=False)

    data = _linehaul_data()
    if expected is None:
        assert "distro" not in data
    else:
        assert data["distro"] == expected


@pytest.mark.parametrize("version", ["15.6", ""])
def test_user_agent_macos(monkeypatch: MonkeyPatch, version: str) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(platform, "mac_ver", lambda: (version, ("", "", ""), ""))

    data = _linehaul_data()
    if version:
        assert data["distro"] == {"name": "macOS", "version": version}
    else:
        assert "distro" not in data


@pytest.mark.parametrize(
    "releaselevel,serial,expected",
    [("final", 0, "7.3.19"), ("beta", 2, "7.3.19.beta.2")],
)
def test_user_agent_pypy(
    monkeypatch: MonkeyPatch, releaselevel: str, serial: int, expected: str
) -> None:
    class PyPyVersionInfo(NamedTuple):
        major: int
        minor: int
        micro: int
        releaselevel: str
        serial: int

    monkeypatch.setattr(platform, "python_implementation", lambda: "PyPy")
    monkeypatch.setattr(
        sys,
        "pypy_version_info",
        PyPyVersionInfo(7, 3, 19, releaselevel, serial),
        raising=False,
    )

    data = _linehaul_data()
    assert data["implementation"] == {"name": "PyPy", "version": expected}
    assert data["python"] == "3.13.5"


def test_user_agent_other_implementation(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(platform, "python_implementation", lambda: "OtherPython")

    assert _linehaul_data()["implementation"] == {
        "name": "OtherPython",
        "version": "3.13.5",
    }


@pytest.mark.parametrize("system", ["Windows", ""])
@pytest.mark.parametrize("release", ["10", ""])
def test_user_agent_optional_system(
    monkeypatch: MonkeyPatch, system: str, release: str
) -> None:
    monkeypatch.setattr(platform, "system", lambda: system)
    monkeypatch.setattr(platform, "release", lambda: release)

    data = _linehaul_data()
    expected = {
        key: value for key, value in (("name", system), ("release", release)) if value
    }
    if expected:
        assert data["system"] == expected
    else:
        assert "system" not in data


def test_user_agent_no_cpu(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(platform, "machine", lambda: "")

    assert "cpu" not in _linehaul_data()


def test_user_agent_no_ssl(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "ssl", None)

    assert "openssl_version" not in _linehaul_data()


def test_user_agent_cached(monkeypatch: MonkeyPatch) -> None:
    user_agent = get_user_agent()
    monkeypatch.setenv("CI", "true")

    assert get_user_agent() == user_agent

    get_user_agent.cache_clear()
    assert get_user_agent() != user_agent
    assert _linehaul_data()["ci"] is True
