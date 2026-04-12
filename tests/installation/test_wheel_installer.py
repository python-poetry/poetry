from __future__ import annotations

import re

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.core.constraints.version import parse_constraint

from poetry.installation.wheel_installer import WheelInstaller
from poetry.utils._compat import WINDOWS
from poetry.utils.env import MockEnv


if TYPE_CHECKING:
    from pytest import TempPathFactory

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
