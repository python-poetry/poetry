import ast
import pytest
import shutil
import tarfile

from poetry.io import NullIO
from poetry.masonry.builders.sdist import SdistBuilder
from poetry.packages import Package
from poetry.poetry import Poetry
from poetry.utils._compat import Path
from poetry.utils.venv import NullVenv

from tests.helpers import get_dependency


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


def project(name):
    return Path(__file__).parent / 'fixtures' / name


def test_convert_dependencies():
    package = Package('foo', '1.2.3')
    result = SdistBuilder.convert_dependencies(
        package,
        [
            get_dependency('A', '^1.0'),
            get_dependency('B', '~1.0'),
            get_dependency('C', '1.2.3'),
        ]
    )
    main = [
        'A>=1.0.0.0,<2.0.0.0',
        'B>=1.0.0.0,<1.1.0.0',
        'C==1.2.3.0',
    ]
    extras = {}

    assert result == (main, extras)

    package = Package('foo', '1.2.3')
    package.extras = {
        'bar': [get_dependency('A')]
    }

    result = SdistBuilder.convert_dependencies(
        package,
        [
            get_dependency('A', '>=1.2', optional=True),
            get_dependency('B', '~1.0'),
            get_dependency('C', '1.2.3'),
        ]
    )
    main = [
        'B>=1.0.0.0,<1.1.0.0',
        'C==1.2.3.0',
    ]
    extras = {
        'bar': ['A>=1.2.0.0']
    }

    assert result == (main, extras)

    c = get_dependency('C', '1.2.3')
    c.python_versions = '~2.7 || ^3.6'
    d = get_dependency('D', '3.4.5', optional=True)
    d.python_versions = '~2.7 || ^3.4'

    package.extras = {
        'baz': [get_dependency('D')]
    }

    result = SdistBuilder.convert_dependencies(
        package,
        [
            get_dependency('A', '>=1.2', optional=True),
            get_dependency('B', '~1.0'),
            c,
            d
        ]
    )
    main = [
        'B>=1.0.0.0,<1.1.0.0',
    ]

    extra_python = (
        ':(python_version >= "2.7.0.0" and python_version < "2.8.0.0") '
        'or (python_version >= "3.6.0.0" and python_version < "4.0.0.0")'
    )
    extra_d_dependency = (
        'baz:(python_version >= "2.7.0.0" and python_version < "2.8.0.0") '
        'or (python_version >= "3.4.0.0" and python_version < "4.0.0.0")'
    )
    extras = {
        extra_python: ['C==1.2.3.0'],
        extra_d_dependency: ['D==3.4.5.0'],
    }

    assert result == (main, extras)


def test_make_setup():
    poetry = Poetry.create(project('complete'))

    builder = SdistBuilder(poetry, NullVenv(), NullIO())
    setup = builder.build_setup()
    setup_ast = ast.parse(setup)

    setup_ast.body = [n for n in setup_ast.body if isinstance(n, ast.Assign)]
    ns = {}
    exec(compile(setup_ast, filename="setup.py", mode="exec"), ns)
    assert ns['packages'] == [
        'my_package',
        'my_package.sub_pkg1',
        'my_package.sub_pkg2'
    ]
    assert ns['install_requires'] == [
        'cleo>=0.6.0.0,<0.7.0.0'
    ]
    assert ns['entry_points'] == {
        'console_scripts': [
            'my-2nd-script = my_package:main2',
            'my-script = my_package:main',
        ]
    }
    assert ns['extras_require'] == {
        'time': [
            'pendulum>=1.4.0.0,<2.0.0.0'
        ]
    }


def test_find_files_to_add():
    poetry = Poetry.create(project('complete'))

    builder = SdistBuilder(poetry, NullVenv(), NullIO())
    result = builder.find_files_to_add()

    assert result == [
        Path('README.rst'),
        Path('my_package/__init__.py'),
        Path('my_package/data1/test.json'),
        Path('my_package/sub_pkg1/__init__.py'),
        Path('my_package/sub_pkg2/__init__.py'),
        Path('my_package/sub_pkg2/data2/data.json'),
        Path('pyproject.toml'),
    ]


def test_package():
    poetry = Poetry.create(project('complete'))

    builder = SdistBuilder(poetry, NullVenv(), NullIO())
    builder.build()

    sdist = fixtures_dir / 'complete' / 'dist' / 'my-package-1.2.3.tar.gz'

    assert sdist.exists()


def test_prelease():
    poetry = Poetry.create(project('prerelease'))

    builder = SdistBuilder(poetry, NullVenv(), NullIO())
    builder.build()

    sdist = fixtures_dir / 'prerelease' / 'dist' / 'prerelease-0.1b1.tar.gz'

    assert sdist.exists()


def test_with_c_extensions():
    poetry = Poetry.create(project('extended'))

    builder = SdistBuilder(poetry, NullVenv(), NullIO())
    builder.build()

    sdist = fixtures_dir / 'extended' / 'dist' / 'extended-0.1.tar.gz'

    assert sdist.exists()

    tar = tarfile.open(str(sdist), 'r')

    assert 'extended-0.1/build.py' in tar.getnames()
    assert 'extended-0.1/extended/extended.c' in tar.getnames()

