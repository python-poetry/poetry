# -*- coding: utf-8 -*-
import pytest
import shutil
import zipfile

from poetry.io import NullIO
from poetry.masonry.builders import WheelBuilder
from poetry.poetry import Poetry
from poetry.utils._compat import Path
from poetry.utils.env import NullEnv


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


def test_wheel_localversionlabel():
    module_path = fixtures_dir / "localversionlabel"
    WheelBuilder.make(Poetry.create(str(module_path)), NullEnv(), NullIO())
    local_version_string = "localversionlabel-0.1b1+gitbranch.buildno.1"
    whl = module_path / "dist" / (local_version_string + "-py2.py3-none-any.whl")

    assert whl.exists()

    with zipfile.ZipFile(str(whl)) as z:
        assert local_version_string + ".dist-info/METADATA" in z.namelist()


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


def test_dist_info_file_permissions():
    module_path = fixtures_dir / "complete"
    WheelBuilder.make(Poetry.create(str(module_path)), NullEnv(), NullIO())

    whl = module_path / "dist" / "my_package-1.2.3-py3-none-any.whl"

    with zipfile.ZipFile(str(whl)) as z:
        assert (
            z.getinfo("my_package-1.2.3.dist-info/WHEEL").external_attr == 0o644 << 16
        )
        assert (
            z.getinfo("my_package-1.2.3.dist-info/METADATA").external_attr
            == 0o644 << 16
        )
        assert (
            z.getinfo("my_package-1.2.3.dist-info/RECORD").external_attr == 0o644 << 16
        )
        assert (
            z.getinfo("my_package-1.2.3.dist-info/entry_points.txt").external_attr
            == 0o644 << 16
        )
