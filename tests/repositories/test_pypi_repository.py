import json

from poetry.repositories.pypi_repository import PyPiRepository
from poetry.utils._compat import Path


class MockRepository(PyPiRepository):

    FIXTURES = Path(__file__).parent / 'fixtures' / 'pypi.org' / 'json'

    def __init__(self):
        super(MockRepository, self).__init__(
            url='http://foo.bar',
            disable_cache=True
        )

    def _get(self, url):
        fixture = self.FIXTURES / 'requests.json'

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
