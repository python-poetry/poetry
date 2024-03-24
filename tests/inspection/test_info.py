from __future__ import annotations

import shutil

from subprocess import CalledProcessError
from typing import TYPE_CHECKING
from zipfile import ZipFile

import pytest

from packaging.metadata import parse_email

from poetry.inspection.info import PackageInfo
from poetry.inspection.info import PackageInfoError
from poetry.utils.env import EnvCommandError
from poetry.utils.env import VirtualEnv


if TYPE_CHECKING:
    from pathlib import Path

    from packaging.metadata import RawMetadata
    from pytest_mock import MockerFixture

    from tests.types import FixtureDirGetter


@pytest.fixture(autouse=True)
def pep517_metadata_mock() -> None:
    pass


@pytest.fixture
def demo_sdist(fixture_dir: FixtureDirGetter) -> Path:
    return fixture_dir("distributions") / "demo-0.1.0.tar.gz"


@pytest.fixture
def demo_wheel(fixture_dir: FixtureDirGetter) -> Path:
    return fixture_dir("distributions") / "demo-0.1.0-py2.py3-none-any.whl"


@pytest.fixture
def demo_wheel_metadata(demo_wheel: Path) -> RawMetadata:
    with ZipFile(demo_wheel) as zf:
        metadata, _ = parse_email(zf.read("demo-0.1.0.dist-info/METADATA"))
    return metadata


@pytest.fixture
def source_dir(tmp_path: Path) -> Path:
    path = tmp_path / "source"
    path.mkdir()
    return path


@pytest.fixture
def demo_setup(source_dir: Path) -> Path:
    setup_py = source_dir / "setup.py"
    setup_py.write_text(
        "from setuptools import setup; "
        'setup(name="demo", '
        'version="0.1.0", '
        'install_requires=["package"])'
    )
    return source_dir


@pytest.fixture
def demo_setup_cfg(source_dir: Path) -> Path:
    setup_cfg = source_dir / "setup.cfg"
    setup_cfg.write_text(
        "\n".join(
            [
                "[metadata]",
                "name = demo",
                "version = 0.1.0",
                "[options]",
                "install_requires = package",
            ]
        )
    )
    return source_dir


@pytest.fixture
def demo_setup_complex(source_dir: Path) -> Path:
    setup_py = source_dir / "setup.py"
    setup_py.write_text(
        "from setuptools import setup; "
        'setup(name="demo", '
        'version="0.1.0", '
        'install_requires=[i for i in ["package"]])'
    )
    return source_dir


@pytest.fixture
def demo_setup_complex_pep517_legacy(demo_setup_complex: Path) -> Path:
    pyproject_toml = demo_setup_complex / "pyproject.toml"
    pyproject_toml.write_text('[build-system]\nrequires = ["setuptools", "wheel"]')
    return demo_setup_complex


@pytest.fixture
def demo_setup_complex_calls_script(
    fixture_dir: FixtureDirGetter, source_dir: Path, tmp_path: Path
) -> Path:
    # make sure the scripts project is on the same drive (for Windows tests in CI)
    scripts_dir = tmp_path / "scripts"
    shutil.copytree(fixture_dir("scripts"), scripts_dir)

    pyproject = source_dir / "pyproject.toml"
    pyproject.write_text(
        f"""\
    [build-system]
    requires = ["setuptools", "scripts @ {scripts_dir.as_uri()}"]
    build-backend = "setuptools.build_meta:__legacy__"
"""
    )

    setup_py = source_dir / "setup.py"
    setup_py.write_text(
        """\
import subprocess
from setuptools import setup
if subprocess.call(["exit-code"]) != 42:
    raise RuntimeError("Wrong exit code.")
setup(name="demo", version="0.1.0", install_requires=[i for i in ["package"]])
"""
    )

    return source_dir


def demo_check_info(info: PackageInfo, requires_dist: set[str] | None = None) -> None:
    assert info.name == "demo"
    assert info.version == "0.1.0"
    assert info.requires_dist

    if requires_dist:
        assert set(info.requires_dist) == requires_dist
    else:
        assert set(info.requires_dist) in (
            # before https://github.com/python-poetry/poetry-core/pull/510
            {
                'cleo; extra == "foo"',
                "pendulum (>=1.4.4)",
                'tomlkit; extra == "bar"',
            },
            # after https://github.com/python-poetry/poetry-core/pull/510
            {
                'cleo ; extra == "foo"',
                "pendulum (>=1.4.4)",
                'tomlkit ; extra == "bar"',
            },
        )


def test_info_from_sdist(demo_sdist: Path) -> None:
    info = PackageInfo.from_sdist(demo_sdist)
    demo_check_info(info)
    assert info._source_type == "file"
    assert info._source_url == demo_sdist.resolve().as_posix()


def test_info_from_sdist_no_pkg_info(fixture_dir: FixtureDirGetter) -> None:
    path = fixture_dir("distributions") / "demo_no_pkg_info-0.1.0.tar.gz"
    info = PackageInfo.from_sdist(path)
    demo_check_info(info)
    assert info._source_type == "file"
    assert info._source_url == path.resolve().as_posix()


def test_info_from_wheel(demo_wheel: Path) -> None:
    info = PackageInfo.from_wheel(demo_wheel)
    demo_check_info(info)
    assert info._source_type == "file"
    assert info._source_url == demo_wheel.resolve().as_posix()


def test_info_from_wheel_metadata_version_unknown(
    fixture_dir: FixtureDirGetter,
) -> None:
    path = (
        fixture_dir("distributions")
        / "demo_metadata_version_unknown-0.1.0-py2.py3-none-any.whl"
    )

    with pytest.raises(PackageInfoError) as e:
        PackageInfo.from_wheel(path)

    assert "Unknown metadata version: 999.3" in str(e.value)


def test_info_from_wheel_metadata(demo_wheel_metadata: RawMetadata) -> None:
    info = PackageInfo.from_metadata(demo_wheel_metadata)
    demo_check_info(info)
    assert info.requires_python == ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*"
    assert info._source_type is None
    assert info._source_url is None


def test_info_from_wheel_metadata_incomplete() -> None:
    """
    To avoid differences in cached metadata,
    it is important that the representation of missing fields does not change!
    """
    metadata, _ = parse_email(b"Metadata-Version: 2.1\nName: demo\nVersion: 0.1.0\n")
    info = PackageInfo.from_metadata(metadata)
    assert info.name == "demo"
    assert info.version == "0.1.0"
    assert info.summary is None
    assert info.requires_dist is None
    assert info.requires_python is None


def test_info_from_bdist(demo_wheel: Path) -> None:
    info = PackageInfo.from_bdist(demo_wheel)
    demo_check_info(info)
    assert info._source_type == "file"
    assert info._source_url == demo_wheel.resolve().as_posix()


def test_info_from_poetry_directory(fixture_dir: FixtureDirGetter) -> None:
    info = PackageInfo.from_directory(
        fixture_dir("inspection") / "demo", disable_build=True
    )
    demo_check_info(info)


def test_info_from_poetry_directory_fallback_on_poetry_create_error(
    mocker: MockerFixture, fixture_dir: FixtureDirGetter
) -> None:
    mock_create_poetry = mocker.patch(
        "poetry.inspection.info.Factory.create_poetry", side_effect=RuntimeError
    )
    mock_get_poetry_package = mocker.spy(PackageInfo, "_get_poetry_package")
    mock_get_pep517_metadata = mocker.patch(
        "poetry.inspection.info.get_pep517_metadata"
    )

    PackageInfo.from_directory(fixture_dir("inspection") / "demo_poetry_package")

    assert mock_create_poetry.call_count == 1
    assert mock_get_poetry_package.call_count == 1
    assert mock_get_pep517_metadata.call_count == 1


def test_info_from_requires_txt(fixture_dir: FixtureDirGetter) -> None:
    info = PackageInfo.from_metadata_directory(
        fixture_dir("inspection") / "demo_only_requires_txt.egg-info"
    )
    assert info is not None
    demo_check_info(info)


def test_info_from_setup_py(demo_setup: Path) -> None:
    info = PackageInfo.from_setup_files(demo_setup)
    demo_check_info(info, requires_dist={"package"})


def test_info_from_setup_cfg(demo_setup_cfg: Path) -> None:
    info = PackageInfo.from_setup_files(demo_setup_cfg)
    demo_check_info(info, requires_dist={"package"})


def test_info_no_setup_pkg_info_no_deps(fixture_dir: FixtureDirGetter) -> None:
    info = PackageInfo.from_directory(
        fixture_dir("inspection") / "demo_no_setup_pkg_info_no_deps",
        disable_build=True,
    )
    assert info.name == "demo"
    assert info.version == "0.1.0"
    assert info.requires_dist is None


def test_info_setup_simple(mocker: MockerFixture, demo_setup: Path) -> None:
    spy = mocker.spy(VirtualEnv, "run")
    info = PackageInfo.from_directory(demo_setup)
    assert spy.call_count == 0
    demo_check_info(info, requires_dist={"package"})


def test_info_setup_cfg(mocker: MockerFixture, demo_setup_cfg: Path) -> None:
    spy = mocker.spy(VirtualEnv, "run")
    info = PackageInfo.from_directory(demo_setup_cfg)
    assert spy.call_count == 0
    demo_check_info(info, requires_dist={"package"})


@pytest.mark.network
def test_info_setup_complex(demo_setup_complex: Path) -> None:
    info = PackageInfo.from_directory(demo_setup_complex)
    demo_check_info(info, requires_dist={"package"})


def test_info_setup_complex_pep517_error(
    mocker: MockerFixture, demo_setup_complex: Path
) -> None:
    mocker.patch(
        "poetry.utils.env.VirtualEnv.run",
        autospec=True,
        side_effect=EnvCommandError(CalledProcessError(1, "mock", output="mock")),
    )

    with pytest.raises(PackageInfoError):
        PackageInfo.from_directory(demo_setup_complex)


@pytest.mark.network
def test_info_setup_complex_pep517_legacy(
    demo_setup_complex_pep517_legacy: Path,
) -> None:
    info = PackageInfo.from_directory(demo_setup_complex_pep517_legacy)
    demo_check_info(info, requires_dist={"package"})


def test_info_setup_complex_disable_build(
    mocker: MockerFixture, demo_setup_complex: Path
) -> None:
    # Cannot extract install_requires from list comprehension.
    with pytest.raises(PackageInfoError):
        PackageInfo.from_directory(demo_setup_complex, disable_build=True)


@pytest.mark.network
def test_info_setup_complex_calls_script(demo_setup_complex_calls_script: Path) -> None:
    """Building the project requires calling a script from its build_requires."""
    info = PackageInfo.from_directory(demo_setup_complex_calls_script)
    demo_check_info(info, requires_dist={"package"})


@pytest.mark.network
@pytest.mark.parametrize("missing", ["version", "name", "install_requires"])
def test_info_setup_missing_mandatory_should_trigger_pep517(
    mocker: MockerFixture, source_dir: Path, missing: str
) -> None:
    setup = "from setuptools import setup; "
    setup += "setup("
    setup += 'name="demo", ' if missing != "name" else ""
    setup += 'version="0.1.0", ' if missing != "version" else ""
    setup += 'install_requires=["package"]' if missing != "install_requires" else ""
    setup += ")"

    setup_py = source_dir / "setup.py"
    setup_py.write_text(setup)

    spy = mocker.spy(VirtualEnv, "run")
    _ = PackageInfo.from_directory(source_dir)
    assert spy.call_count == 1


def test_info_prefer_poetry_config_over_egg_info(fixture_dir: FixtureDirGetter) -> None:
    info = PackageInfo.from_directory(
        fixture_dir("inspection") / "demo_with_obsolete_egg_info"
    )
    demo_check_info(info)
