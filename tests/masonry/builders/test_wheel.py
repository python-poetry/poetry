import pytest
import shutil
import zipfile

from clikit.io import NullIO

from poetry.masonry.builders import WheelBuilder
from poetry.poetry import Poetry
from poetry.utils._compat import Path
from poetry.utils.env import NullEnv
from poetry.packages import ProjectPackage


fixtures_dir = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def setup():
    clear_samples_dist()

    yield

    clear_samples_dist()


def clear_samples_dist():
    for dist in fixtures_dir.glob("**/dist"):
        if dist.is_dir():
            shutil.rmtree(str(dist))


def test_wheel_module():
    module_path = fixtures_dir / "module1"
    WheelBuilder.make(Poetry.create(str(module_path)), NullEnv(), NullIO())

    whl = module_path / "dist" / "module1-0.1-py2.py3-none-any.whl"

    assert whl.exists()

    with zipfile.ZipFile(str(whl)) as z:
        assert "module1.py" in z.namelist()


def test_wheel_package():
    module_path = fixtures_dir / "complete"
    WheelBuilder.make(Poetry.create(str(module_path)), NullEnv(), NullIO())

    whl = module_path / "dist" / "my_package-1.2.3-py3-none-any.whl"

    assert whl.exists()

    with zipfile.ZipFile(str(whl)) as z:
        assert "my_package/sub_pkg1/__init__.py" in z.namelist()


def test_wheel_prerelease():
    module_path = fixtures_dir / "prerelease"
    WheelBuilder.make(Poetry.create(str(module_path)), NullEnv(), NullIO())

    whl = module_path / "dist" / "prerelease-0.1b1-py2.py3-none-any.whl"

    assert whl.exists()


def test_wheel_package_src():
    module_path = fixtures_dir / "source_package"
    WheelBuilder.make(Poetry.create(str(module_path)), NullEnv(), NullIO())

    whl = module_path / "dist" / "package_src-0.1-py2.py3-none-any.whl"

    assert whl.exists()

    with zipfile.ZipFile(str(whl)) as z:
        assert "package_src/__init__.py" in z.namelist()
        assert "package_src/module.py" in z.namelist()


def test_wheel_module_src():
    module_path = fixtures_dir / "source_file"
    WheelBuilder.make(Poetry.create(str(module_path)), NullEnv(), NullIO())

    whl = module_path / "dist" / "module_src-0.1-py2.py3-none-any.whl"

    assert whl.exists()

    with zipfile.ZipFile(str(whl)) as z:
        assert "module_src.py" in z.namelist()


def test_package_with_include(mocker):
    # Patch git module to return specific excluded files
    p = mocker.patch("poetry.vcs.git.Git.get_ignored_files")
    p.return_value = [
        str(
            Path(__file__).parent
            / "fixtures"
            / "with-include"
            / "extra_dir"
            / "vcs_excluded.txt"
        ),
        str(
            Path(__file__).parent
            / "fixtures"
            / "with-include"
            / "extra_dir"
            / "sub_pkg"
            / "vcs_excluded.txt"
        ),
    ]
    module_path = fixtures_dir / "with-include"
    WheelBuilder.make(Poetry.create(str(module_path)), NullEnv(), NullIO())

    whl = module_path / "dist" / "with_include-1.2.3-py3-none-any.whl"

    assert whl.exists()

    with zipfile.ZipFile(str(whl)) as z:
        names = z.namelist()
        assert len(names) == len(set(names))
        assert "with_include-1.2.3.dist-info/LICENSE" in names
        assert "extra_dir/__init__.py" in names
        assert "extra_dir/vcs_excluded.txt" in names
        assert "extra_dir/sub_pkg/__init__.py" in names
        assert "extra_dir/sub_pkg/vcs_excluded.txt" not in names
        assert "my_module.py" in names
        assert "notes.txt" in names
        assert "package_with_include/__init__.py" in names


def test_write_metadata_file_license_homepage_default(mocker):
    # Preparation
    mocked_poetry = mocker.Mock()
    mocked_poetry.file.parent = Path(".")
    mocked_poetry.package = ProjectPackage("pkg_name", "1.0.0")
    mocked_file = mocker.Mock()
    mocked_venv = mocker.Mock()
    mocked_io = mocker.Mock()
    # patch Module init inside Builder class
    mocker.patch("poetry.masonry.builders.builder.Module")
    w = WheelBuilder(mocked_poetry, mocked_venv, mocked_io)

    # Action
    w._write_metadata_file(mocked_file)

    # Assertion
    mocked_file.write.assert_any_call("Home-page: UNKNOWN\n")
    mocked_file.write.assert_any_call("License: UNKNOWN\n")
