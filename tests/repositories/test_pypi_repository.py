import json

from poetry.repositories.pypi_repository import PyPiRepository
from poetry.utils._compat import Path


class MockRepository(PyPiRepository):

    FIXTURES = Path(__file__).parent / 'fixtures' / 'pypi.org' / 'json'

    def __init__(self):
        super(MockRepository, self).__init__(
            url='http://foo.bar',
            disable_cache=True,
            fallback=False
        )

    def _get(self, url):
        parts = url.split('/')[1:]
        name = parts[0]
        if len(parts) == 3:
            version = parts[1]
        else:
            version = None

        if not version:
            fixture = self.FIXTURES / (name + '.json')
        else:
            fixture = self.FIXTURES / name / (version + '.json')
            if not fixture.exists():
                fixture = self.FIXTURES / (name + '.json')

        with fixture.open() as f:
            return json.loads(f.read())


def test_find_packages():
    repo = MockRepository()
    packages = repo.find_packages('requests', '^2.18')

    assert len(packages) == 5


def test_package():
    repo = MockRepository()

    package = repo.package('requests', '2.18.4')

    assert package.name == 'requests'
    assert len(package.requires) == 4
    assert len(package.extras['security']) == 3
    assert len(package.extras['socks']) == 2

    win_inet = package.extras['socks'][0]
    assert win_inet.name == 'win-inet-pton'
    assert win_inet.python_versions == '~2.7 || ~2.6'
    assert win_inet.platform == 'win32'


def test_package_drops_malformed_dependencies():
    repo = MockRepository()

    package = repo.package('ipython', '4.1.0rc1')
    dependency_names = [d.name for d in package.requires]

    assert 'setuptools' not in dependency_names


def test_parse_requires():
    requires = """\
jsonschema>=2.6.0.0,<3.0.0.0
lockfile>=0.12.0.0,<0.13.0.0
pip-tools>=1.11.0.0,<2.0.0.0
pkginfo>=1.4.0.0,<2.0.0.0
pyrsistent>=0.14.2.0,<0.15.0.0
toml>=0.9.0.0,<0.10.0.0
cleo>=0.6.0.0,<0.7.0.0
cachy>=0.1.1.0,<0.2.0.0
cachecontrol>=0.12.4.0,<0.13.0.0
requests>=2.18.0.0,<3.0.0.0
msgpack-python>=0.5.0.0,<0.6.0.0
pyparsing>=2.2.0.0,<3.0.0.0
requests-toolbelt>=0.8.0.0,<0.9.0.0

[:(python_version >= "2.7.0.0" and python_version < "2.8.0.0") or (python_version >= "3.4.0.0" and python_version < "3.5.0.0")]
typing>=3.6.0.0,<4.0.0.0

[:python_version >= "2.7.0.0" and python_version < "2.8.0.0"]
virtualenv>=15.2.0.0,<16.0.0.0
pathlib2>=2.3.0.0,<3.0.0.0

[:python_version >= "3.4.0.0" and python_version < "3.6.0.0"]
zipfile36>=0.1.0.0,<0.2.0.0    
"""
    result = MockRepository()._parse_requires(requires)
    expected = [
        'jsonschema>=2.6.0.0,<3.0.0.0',
        'lockfile>=0.12.0.0,<0.13.0.0',
        'pip-tools>=1.11.0.0,<2.0.0.0',
        'pkginfo>=1.4.0.0,<2.0.0.0',
        'pyrsistent>=0.14.2.0,<0.15.0.0',
        'toml>=0.9.0.0,<0.10.0.0',
        'cleo>=0.6.0.0,<0.7.0.0',
        'cachy>=0.1.1.0,<0.2.0.0',
        'cachecontrol>=0.12.4.0,<0.13.0.0',
        'requests>=2.18.0.0,<3.0.0.0',
        'msgpack-python>=0.5.0.0,<0.6.0.0',
        'pyparsing>=2.2.0.0,<3.0.0.0',
        'requests-toolbelt>=0.8.0.0,<0.9.0.0',
        'typing>=3.6.0.0,<4.0.0.0; (python_version >= "2.7.0.0" and python_version < "2.8.0.0") or (python_version >= "3.4.0.0" and python_version < "3.5.0.0")',
        'virtualenv>=15.2.0.0,<16.0.0.0; python_version >= "2.7.0.0" and python_version < "2.8.0.0"',
        'pathlib2>=2.3.0.0,<3.0.0.0; python_version >= "2.7.0.0" and python_version < "2.8.0.0"',
        'zipfile36>=0.1.0.0,<0.2.0.0; python_version >= "3.4.0.0" and python_version < "3.6.0.0"'
    ]
    assert result == expected
