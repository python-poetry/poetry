import pytest
from mock import MagicMock, mock

from poetry.repositories.legacy_repository import LegacyRepository
from poetry.repositories.legacy_repository import Page
from poetry.utils._compat import Path
from poetry.utils._compat import decode


class MockRepository(LegacyRepository):

    FIXTURES = Path(__file__).parent / "fixtures" / "legacy"

    def __init__(self):
        super(MockRepository, self).__init__(
            "legacy", url="http://foo.bar", disable_cache=True
        )

    def _get(self, endpoint):
        parts = endpoint.split("/")
        name = parts[1]

        fixture = self.FIXTURES / (name + ".html")

        with fixture.open() as f:
            return Page(self._url + endpoint, f.read(), {})


def test_page_relative_links_path_are_correct():
    repo = MockRepository()

    page = repo._get("/relative")

    for link in page.links:
        assert link.netloc == "foo.bar"
        assert link.path.startswith("/relative/poetry")


def test_page_absolute_links_path_are_correct():
    repo = MockRepository()

    page = repo._get("/absolute")

    for link in page.links:
        assert link.netloc == "files.pythonhosted.org"
        assert link.path.startswith("/packages/")


@mock.patch("poetry.repositories.legacy_repository.get_http_basic_auth")
def test_http_basic_auth_repo(mock_get_auth):
    mock_get_auth.return_value = ("user1", "p4ss")

    repo = MockRepository()
    assert "user1:p4ss@" in repo._url
