import importlib.util
import os
import shutil
import tarfile

from pathlib import Path

import pytest


@pytest.fixture()
def poetry_home(tmp_dir) -> Path:
    pth = Path(tmp_dir) / ".poetry"
    return pth


@pytest.fixture()
def get_poetry(poetry_home):
    os.environ["POETRY_HOME"] = str(poetry_home)
    source_home = Path(__file__).parent.parent.parent
    get_poetry_path = source_home / "get-poetry.py"
    spec = importlib.util.spec_from_file_location("getpoetry", get_poetry_path)
    getpoetry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(getpoetry)
    return getpoetry


@pytest.fixture()
def poetry_source_file(tmp_dir):
    source = Path(tmp_dir) / "fake-source"
    source.mkdir()
    poetry_dir = source / "poetry"
    poetry_dir.mkdir()
    (poetry_dir / "poetry.py").touch()
    (poetry_dir / "__init__.py").touch()
    (poetry_dir / "__main__.py").touch()
    (poetry_dir / "__version__.py").touch()
    source_tar = Path(tmp_dir) / "fake-source.tar.gz"
    tar = tarfile.open(source_tar, "w:gz")
    tar.add(poetry_dir, arcname="poetry")
    tar.close()
    shutil.rmtree(source)
    return source_tar


@pytest.fixture()
def poetry_source_file_bad(tmp_dir):
    source = Path(tmp_dir) / "fake-source"
    source.mkdir()
    poetry_dir = source / "foo"
    poetry_dir.mkdir()
    source_tar = Path(tmp_dir) / "fake-source-bad.tar.gz"
    tar = tarfile.open(source_tar, "w:gz")
    tar.add(poetry_dir, arcname="foo")
    tar.close()
    shutil.rmtree(source)
    return source_tar


def test_installer_file_make_lib(poetry_home, poetry_source_file, get_poetry):
    installer = get_poetry.Installer(
        version=None, file=str(poetry_source_file), accept_all=True
    )
    installer.make_lib(None)
    assert poetry_home.is_dir()
    assert (poetry_home / "lib" / "poetry" / "__init__.py").is_file()


def test_installer_file_make_lib_raises_source_file_error(
    poetry_home, poetry_source_file_bad, get_poetry
):
    installer = get_poetry.Installer(
        version=None, file=str(poetry_source_file_bad), accept_all=True
    )
    with pytest.raises(get_poetry.SourceFileError):
        installer.make_lib(None)
