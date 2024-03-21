from __future__ import annotations

import re
import shutil

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.core.constraints.version import parse_constraint

from poetry.installation.wheel_installer import WheelDestinationCopy
from poetry.installation.wheel_installer import WheelInstaller
from poetry.utils.env import MockEnv


if TYPE_CHECKING:
    from _pytest.tmpdir import TempPathFactory

    from tests.types import FixtureDirGetter


@pytest.fixture
def env(tmp_path: Path) -> MockEnv:
    return MockEnv(path=tmp_path)


@pytest.fixture(scope="module")
def demo_wheel(fixture_dir: FixtureDirGetter) -> Path:
    return fixture_dir("distributions/demo-0.1.0-py2.py3-none-any.whl")


@pytest.fixture(scope="module")
def django_wheel(fixture_dir: FixtureDirGetter) -> Path:
    return fixture_dir("distributions/Django-5.0.3-py3-none-any.whl")


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
    with open(installer_file) as f:
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


def delete_tmp_dir_func_factory(tmp_path: Path):
    def delete_tmp_dir():
        shutil.rmtree(tmp_path)
        tmp_path.mkdir()

    return delete_tmp_dir


@pytest.mark.benchmark(
    group="demo_wheel",
)
def test_bench_installer_copy_demo(
    env: MockEnv, demo_wheel: Path, benchmark, tmp_path: Path
) -> None:
    installer = WheelInstaller(env, wheel_destination_class=WheelDestinationCopy)
    benchmark.pedantic(
        installer.install,
        args=(demo_wheel,),
        setup=delete_tmp_dir_func_factory(tmp_path),
        rounds=1000,
    )


@pytest.mark.benchmark(
    group="demo_wheel",
)
def test_bench_installer_demo(
    env: MockEnv, demo_wheel: Path, benchmark, tmp_path: Path
) -> None:
    installer = WheelInstaller(env)
    benchmark.pedantic(
        installer.install,
        args=(demo_wheel,),
        setup=delete_tmp_dir_func_factory(tmp_path),
        rounds=1000,
    )


@pytest.mark.benchmark(
    group="django_wheel",
)
def test_bench_installer_copy_django(
    env: MockEnv, django_wheel: Path, benchmark, tmp_path: Path
) -> None:
    installer = WheelInstaller(env, wheel_destination_class=WheelDestinationCopy)
    benchmark.pedantic(
        installer.install,
        args=(django_wheel,),
        setup=delete_tmp_dir_func_factory(tmp_path),
        rounds=30,
    )


@pytest.mark.benchmark(
    group="django_wheel",
)
def test_bench_installer_django(
    env: MockEnv, django_wheel: Path, benchmark, tmp_path: Path
) -> None:
    installer = WheelInstaller(env)
    benchmark.pedantic(
        installer.install,
        args=(django_wheel,),
        setup=delete_tmp_dir_func_factory(tmp_path),
        rounds=30,
    )
