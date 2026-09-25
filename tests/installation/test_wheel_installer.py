from __future__ import annotations

import re
import threading
import zipfile

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

import installer.utils
import pytest

from poetry.core.constraints.version import parse_constraint

from poetry.installation.wheel_installer import WheelInstaller
from poetry.utils._compat import WINDOWS
from poetry.utils.env import MockEnv


if TYPE_CHECKING:
    from typing import BinaryIO

    from pytest import TempPathFactory
    from pytest_mock import MockerFixture

    from tests.types import FixtureDirGetter


@pytest.fixture
def env(tmp_path: Path) -> MockEnv:
    return MockEnv(path=tmp_path / "env")


@pytest.fixture(scope="module")
def demo_wheel(fixture_dir: FixtureDirGetter) -> Path:
    return fixture_dir("distributions/demo-0.1.0-py2.py3-none-any.whl")


@pytest.fixture(scope="module")
def default_installation(tmp_path_factory: TempPathFactory, demo_wheel: Path) -> Path:
    env = MockEnv(path=tmp_path_factory.mktemp("default_install"))
    installer = WheelInstaller(env)
    installer.install(demo_wheel)
    return Path(env.paths["purelib"])


def test_default_installation_source_dir_content(default_installation: Path) -> None:
    source_dir = default_installation / "demo"
    assert source_dir.exists()
    assert (source_dir / "__init__.py").exists()


def test_default_installation_dist_info_dir_content(default_installation: Path) -> None:
    dist_info_dir = default_installation / "demo-0.1.0.dist-info"
    assert dist_info_dir.exists()
    assert (dist_info_dir / "INSTALLER").exists()
    assert (dist_info_dir / "METADATA").exists()
    assert (dist_info_dir / "RECORD").exists()
    assert (dist_info_dir / "WHEEL").exists()


def test_installer_file_contains_valid_version(default_installation: Path) -> None:
    installer_file = default_installation / "demo-0.1.0.dist-info" / "INSTALLER"
    with open(installer_file, encoding="utf-8") as f:
        installer_content = f.read()
    match = re.match(r"Poetry (?P<version>.*)", installer_content)
    assert match
    parse_constraint(match.group("version"))  # must not raise an error


def test_default_installation_no_bytecode(default_installation: Path) -> None:
    cache_dir = default_installation / "demo" / "__pycache__"
    assert not cache_dir.exists()


@pytest.mark.parametrize("compile", [True, False])
def test_enable_bytecode_compilation(
    env: MockEnv, demo_wheel: Path, compile: bool
) -> None:
    installer = WheelInstaller(env)
    installer.enable_bytecode_compilation(compile)
    installer.install(demo_wheel)
    cache_dir = Path(env.paths["purelib"]) / "demo" / "__pycache__"
    if compile:
        assert cache_dir.exists()
        assert list(cache_dir.glob("*.pyc"))
        assert not list(cache_dir.glob("*.opt-1.pyc"))
        assert not list(cache_dir.glob("*.opt-2.pyc"))
    else:
        assert not cache_dir.exists()


def test_install_dir_is_symlink(tmp_path: Path, demo_wheel: Path) -> None:
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    symlink_dir = tmp_path / "symlink"
    symlink_dir.symlink_to(target_dir, target_is_directory=True)

    env = MockEnv(path=symlink_dir)

    installer = WheelInstaller(env)
    installer.install(demo_wheel)

    assert (Path(env.paths["purelib"]) / "demo").exists()


@pytest.mark.parametrize("existing", [False, True])
def test_no_path_traversal(
    env: MockEnv, wheel_with_path_traversal: Path, existing: bool
) -> None:
    """see also test_extractall_wheel_no_path_traversal in test_helpers.py"""
    target = env.path.parent / "traversal.txt"
    if existing:
        target.write_text("original", encoding="utf-8")
    installer = WheelInstaller(env)
    with pytest.raises(ValueError):
        installer.install(wheel_with_path_traversal)

    if existing:
        assert target.exists()
        assert target.read_text(encoding="utf-8") == "original"
    else:
        assert not target.exists()


@pytest.mark.parametrize("existing", [False, True])
def test_no_path_traversal_via_symlink(
    tmp_path: Path,
    env: MockEnv,
    wheel_with_path_traversal_via_symlink: Path,
    existing: bool,
) -> None:
    """see also test_extractall_wheel_no_path_traversal_via_symlink
    in test_helpers.py"""
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    target = target_dir / "traversal.txt"
    if existing:
        target.write_text("original", encoding="utf-8")

    installer = WheelInstaller(env)
    with pytest.raises(FileNotFoundError if WINDOWS else NotADirectoryError):
        installer.install(wheel_with_path_traversal_via_symlink)

    traversal_link = Path(env.paths["purelib"]) / "symlink" / "traversal_link"
    assert traversal_link.exists()
    assert not traversal_link.is_symlink()  # not even extracted as symlink
    assert target_dir.exists()
    if existing:
        assert target.read_text(encoding="utf-8") == "original"
    else:
        assert not list(target_dir.iterdir())


def _build_wheel(directory: Path, name: str, files: dict[str, bytes]) -> Path:
    dist_info = f"{name}-0.1.dist-info"
    files = {
        **files,
        f"{dist_info}/WHEEL": (
            b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
        ),
        f"{dist_info}/METADATA": (
            f"Metadata-Version: 2.1\nName: {name}\nVersion: 0.1\n".encode()
        ),
    }
    files[f"{dist_info}/RECORD"] = (
        "\n".join([f"{k},," for k in files] + [f"{dist_info}/RECORD,,"]) + "\n"
    ).encode()

    wheel = directory / f"{name}-0.1-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as z:
        for k, v in files.items():
            z.writestr(k, v)

    return wheel


def test_parallel_installation_of_file_contained_in_several_wheels(
    tmp_path: Path, env: MockEnv, mocker: MockerFixture
) -> None:
    """
    Several wheels may contain the same file, e.g. the __init__.py
    of a pkgutil-style namespace package. If such wheels are installed
    in parallel, the file must not end up with interleaved contents.
    """
    shared_file = "namespace/__init__.py"
    content_first = b"# first\n" * 100
    content_second = b"# second\n"
    wheel_first = _build_wheel(tmp_path, "first", {shared_file: content_first})
    wheel_second = _build_wheel(tmp_path, "second", {shared_file: content_second})
    target = Path(env.paths["purelib"]) / shared_file

    first_write_started = threading.Event()
    second_write_finished = threading.Event()
    copyfileobj_with_hashing = installer.utils.copyfileobj_with_hashing

    class PausingWriter:
        """Write a part of the data and pause to give the other thread the chance
        to write the same file before the rest of the data is written."""

        def __init__(self, dest: BinaryIO) -> None:
            self._dest = dest

        def write(self, data: bytes) -> int:
            written = self._dest.write(data[:10])
            self._dest.flush()
            first_write_started.set()
            # If writes of the same file are serialized,
            # the second write cannot finish and the wait times out.
            second_write_finished.wait(timeout=1)
            return written + self._dest.write(data[10:])

    def copy(source: BinaryIO, dest: BinaryIO, hash_algorithm: str) -> tuple[str, int]:
        if Path(dest.name) != target:
            return copyfileobj_with_hashing(source, dest, hash_algorithm)
        if not first_write_started.is_set():
            return copyfileobj_with_hashing(
                source,
                PausingWriter(dest),  # type: ignore[arg-type]
                hash_algorithm,
            )
        result = copyfileobj_with_hashing(source, dest, hash_algorithm)
        second_write_finished.set()
        return result

    mocker.patch("installer.utils.copyfileobj_with_hashing", new=copy)

    wheel_installer = WheelInstaller(env)

    def install_second() -> None:
        assert first_write_started.wait(timeout=10)
        wheel_installer.install(wheel_second)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(wheel_installer.install, wheel_first),
            executor.submit(install_second),
        ]
        for future in futures:
            future.result()

    # The file written last wins.
    assert target.read_bytes() == content_second
