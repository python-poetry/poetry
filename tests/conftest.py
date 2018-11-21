import os
import pytest
import shutil
import tempfile

try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

from poetry.config import Config
from poetry.utils._compat import Path
from poetry.utils.toml_file import TomlFile


@pytest.fixture
def tmp_dir():
    dir_ = tempfile.mkdtemp(prefix="poetry_")

    yield dir_

    shutil.rmtree(dir_)


@pytest.fixture
def config():  # type: () -> Config
    with tempfile.NamedTemporaryFile() as f:
        f.close()

        return Config(TomlFile(f.name))


def mock_clone(_, source, dest):
    # Checking source to determine which folder we need to copy
    parts = urlparse.urlparse(source)

    folder = (
        Path(__file__).parent.parent
        / "fixtures"
        / "git"
        / parts.netloc
        / parts.path.lstrip("/").rstrip(".git")
    )

    shutil.rmtree(str(dest))
    shutil.copytree(str(folder), str(dest))


@pytest.fixture
def environ():
    original_environ = os.environ

    yield os.environ

    os.environ = original_environ


@pytest.fixture(autouse=True)
def git_mock(mocker):
    # Patch git module to not actually clone projects
    mocker.patch("poetry.vcs.git.Git.clone", new=mock_clone)
    mocker.patch("poetry.vcs.git.Git.checkout", new=lambda *_: None)
    p = mocker.patch("poetry.vcs.git.Git.rev_parse")
    p.return_value = "9cf87a285a2d3fbb0b9fa621997b3acc3631ed24"
