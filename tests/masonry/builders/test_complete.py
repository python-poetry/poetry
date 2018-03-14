import pytest
import shutil
import tarfile
import zipfile

from pathlib import Path

from poetry import Poetry
from poetry.io import NullIO
from poetry.masonry.builders import CompleteBuilder
from poetry.utils.venv import NullVenv

fixtures_dir = Path(__file__).parent / 'fixtures'


@pytest.fixture(autouse=True)
def setup():
    clear_samples_dist()

    yield

    clear_samples_dist()


def clear_samples_dist():
    for dist in fixtures_dir.glob('**/dist'):
        if dist.is_dir():
            shutil.rmtree(str(dist))


def test_wheel_c_extension():
    module_path = fixtures_dir / 'extended'
    builder = CompleteBuilder(Poetry.create(module_path), NullVenv(True), NullIO())
    builder.build()

    sdist = fixtures_dir / 'extended' / 'dist' / 'extended-0.1.tar.gz'

    assert sdist.exists()

    tar = tarfile.open(str(sdist), 'r')

    assert 'extended-0.1/build.py' in tar.getnames()
    assert 'extended-0.1/extended/extended.c' in tar.getnames()

    whl = list((module_path / 'dist').glob('extended-0.1-cp3*-cp3*m-*.whl'))[0]

    assert whl.exists()

    zip = zipfile.ZipFile(whl)

    has_compiled_extension = False
    for name in zip.namelist():
        if name.startswith('extended/extended') and name.endswith('.so'):
            has_compiled_extension = True

    assert has_compiled_extension
