import pytest

from poetry.inspection.info import PackageInfo
from poetry.utils._compat import PY35
from poetry.utils._compat import Path


FIXTURE_DIR_BASE = Path(__file__).parent.parent / "fixtures"
FIXTURE_DIR_INSPECTIONS = FIXTURE_DIR_BASE / "inspection"


@pytest.fixture
def demo_sdist():  # type: () -> Path
    return FIXTURE_DIR_BASE / "distributions" / "demo-0.1.0.tar.gz"


@pytest.fixture
def demo_wheel():  # type: () -> Path
    return FIXTURE_DIR_BASE / "distributions" / "demo-0.1.0-py2.py3-none-any.whl"


def demo_check_info(info):  # type: (PackageInfo) -> None
    assert info.name == "demo"
    assert info.version == "0.1.0"
    assert set(info.requires_dist) == {
        'cleo; extra == "foo"',
        "pendulum (>=1.4.4)",
        'tomlkit; extra == "bar"',
    }


def test_info_from_sdist(demo_sdist):
    info = PackageInfo.from_sdist(demo_sdist)
    demo_check_info(info)


def test_info_from_wheel(demo_wheel):
    info = PackageInfo.from_wheel(demo_wheel)
    demo_check_info(info)


def test_info_from_bdist(demo_wheel):
    info = PackageInfo.from_bdist(demo_wheel)
    demo_check_info(info)


def test_info_from_poetry_directory():
    info = PackageInfo.from_directory(FIXTURE_DIR_INSPECTIONS / "demo")
    demo_check_info(info)


def test_info_from_requires_txt():
    info = PackageInfo.from_metadata(
        FIXTURE_DIR_INSPECTIONS / "demo_only_requires_txt.egg-info"
    )
    demo_check_info(info)


@pytest.mark.skipif(not PY35, reason="Parsing of setup.py is skipped for Python < 3.5")
def test_info_from_setup_py():
    info = PackageInfo.from_setup_py(FIXTURE_DIR_INSPECTIONS / "demo_only_setup")
    demo_check_info(info)


def test_info_no_setup_pkg_info_no_deps():
    info = PackageInfo.from_directory(
        FIXTURE_DIR_INSPECTIONS / "demo_no_setup_pkg_info_no_deps"
    )
    assert info.name == "demo"
    assert info.version == "0.1.0"
    assert info.requires_dist is None
