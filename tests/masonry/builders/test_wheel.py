import pytest
import shutil

from pathlib import Path

from poetry import Poetry
from poetry.io import NullIO
from poetry.masonry.builders import WheelBuilder


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


def test_wheel_module():
    module_path = fixtures_dir / 'module1'
    WheelBuilder.make(Poetry.create(str(module_path)), NullIO())

    whl = module_path / 'dist' / 'module1-0.1-py2.py3-none-any.whl'

    assert whl.exists()


def test_wheel_package():
    module_path = fixtures_dir / 'complete'
    WheelBuilder.make(Poetry.create(str(module_path)), NullIO())

    whl = module_path / 'dist' / 'my_package-1.2.3-py3-none-any.whl'

    assert whl.exists()


def test_wheel_prerelease():
    module_path = fixtures_dir / 'prerelease'
    WheelBuilder.make(Poetry.create(str(module_path)), NullIO())

    whl = module_path / 'dist' / 'prerelease-0.1b1-py2.py3-none-any.whl'

    assert whl.exists()
