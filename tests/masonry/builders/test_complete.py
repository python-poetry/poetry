import pytest
import re
import shutil
import tarfile
import zipfile

from pathlib import Path

from poetry import __version__
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

    try:
        wheel_data = zip.read('extended-0.1.dist-info/WHEEL').decode()

        assert re.match("""(?m)^\
Wheel-Version: 1.0
Generator: poetry {}
Root-Is-Purelib: false
Tag: cp3\d-cp3\dm-.+
$""".format(__version__), wheel_data) is not None
    finally:
        zip.close()


def test_complete():
    module_path = fixtures_dir / 'complete'
    builder = CompleteBuilder(Poetry.create(module_path), NullVenv(True),
                              NullIO())
    builder.build()

    whl = module_path / 'dist' / 'my_package-1.2.3-py3-none-any.whl'

    assert whl.exists

    zip = zipfile.ZipFile(whl)

    try:
        entry_points = zip.read('my_package-1.2.3.dist-info/entry_points.txt')

        assert entry_points.decode() == """\
[console_scripts]
my-2nd-script=my_package:main2
my-script=my_package:main

"""
        wheel_data = zip.read('my_package-1.2.3.dist-info/WHEEL').decode()

        assert wheel_data == f"""\
Wheel-Version: 1.0
Generator: poetry {__version__}
Root-Is-Purelib: true
Tag: py3-none-any
"""
    finally:
        zip.close()
