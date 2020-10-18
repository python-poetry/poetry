import os
import shutil


try:
    # Python 3.5+
    import importlib.util
except ImportError:
    # Python 2.7
    import imp

from pathlib import Path

import pytest

from poetry.core.masonry.builder import Builder
from poetry.factory import Factory


# We need to set the poetry home environment variable prior to importing the script since it gets set once at import
# time.
SOURCE_HOME = Path(__file__).parent.parent.parent
GET_POETRY_PATH = SOURCE_HOME / "get-poetry.py"
TMP_DIR = Path(__file__).parent / "tmp"
POETRY_HOME = TMP_DIR / ".poetry"
os.environ["POETRY_HOME"] = str(POETRY_HOME)
try:
    # Python 3.5+
    spec = importlib.util.spec_from_file_location("getpoetry", GET_POETRY_PATH)
    getpoetry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(getpoetry)
except ImportError:
    # Python 2.7

    getpoetry = imp.load_source("getpoetry", str(GET_POETRY_PATH))


@pytest.fixture()
def tmp_dir():
    """
    Use this in tests to actually set up and tear down the directory.
    """
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(exist_ok=True, parents=False)
    yield TMP_DIR
    shutil.rmtree(TMP_DIR)


@pytest.fixture()
def poetry_home(tmp_dir):
    return POETRY_HOME


@pytest.fixture()
def poetry_sdist_file(tmp_dir):
    poetry = Factory().create_poetry(cwd=SOURCE_HOME)
    builder = Builder(poetry)
    builder.build("sdist")
    dist_dir = SOURCE_HOME / "dist"
    yield Path(next(dist_dir.glob("*.tar.gz")))


def test_installer_file_sdist(poetry_home, poetry_sdist_file):
    installer = getpoetry.Installer(file=str(poetry_sdist_file), accept_all=True)
    installer.run()
    assert poetry_home.is_dir()
    assert (poetry_home / "bin" / "poetry").is_file()
    assert (poetry_home / "lib" / "poetry" / "__init__.py").is_file()
