import shutil

from poetry.packages.utils.link import Link
from poetry.repositories.find_links_repository import FilteredPage
from poetry.repositories.find_links_repository import FindLinksRepository
from poetry.repositories.find_links_repository import SingleLink
from poetry.utils._compat import Path

from .test_legacy_repository import MockRepository as LegacyMockRepository


try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse


TEST_PACKAGES = ["isort", "futures"]


class MockRepository(FindLinksRepository):

    FIXTURES = Path(__file__).parent / "fixtures" / "find_links"

    def __init__(self, url="http://foo.com/bar/index.html", auth=None):
        super(MockRepository, self).__init__(
            "find_links", url=url, auth=auth, disable_cache=True
        )

    def _get(self, name):
        if self.single_link:
            return SingleLink(self.full_url, name)
        else:
            fixture = self.FIXTURES / "index.html"
            if not fixture.exists():
                return

            with fixture.open(encoding="utf-8") as f:
                return FilteredPage(self.full_url, name, f.read(), {})

    def _download(self, url, dest):
        filename = urlparse.urlparse(url).path.rsplit("/")[-1]
        filepath = self.FIXTURES.parent / "pypi.org" / "dists" / filename

        shutil.copyfile(str(filepath), dest)


def test_url_parsing():
    test_data = {
        "http://foo.com/bar/index.html": {
            "url": "http://foo.com/bar",
            "file_path": "index.html",
            "full_url": "http://foo.com/bar/index.html",
        },
        "http://foo.com/bar/": {
            "url": "http://foo.com/bar",
            "file_path": "",
            "full_url": "http://foo.com/bar/",
        },
        "http://foo.com/bar": {
            "url": "http://foo.com/bar",
            "file_path": "",
            "full_url": "http://foo.com/bar/",
        },
        "http://foo.com/bar/poetry-0.1.0-py3-none-any.whl": {
            "url": "http://foo.com/bar",
            "file_path": "poetry-0.1.0-py3-none-any.whl",
            "full_url": "http://foo.com/bar/poetry-0.1.0-py3-none-any.whl",
        },
    }
    for url, target_data in test_data.items():
        repo = MockRepository(url)
        assert repo.url == target_data["url"]
        assert repo.file_path == target_data["file_path"]
        assert repo.full_url == target_data["full_url"]


def test_page():
    repo = MockRepository()
    legacy_repo = LegacyMockRepository()

    for package_name in TEST_PACKAGES:
        page = repo._get(package_name)
        legacy_page = legacy_repo._get(package_name)

        links = list(page.links)
        legacy_links = list(legacy_page.links)
        assert len(links) == len(legacy_links)
        for l1, l2 in zip(page.links, legacy_page.links):
            assert l1 == l2

    page = repo._get("poetry")
    link = list(page.links)[0]
    assert link.url == "http://foo.com/bar/relative/poetry-0.1.0-py3-none-any.whl"


def test_find_packages():
    repo = MockRepository()
    legacy_repo = LegacyMockRepository()
    for package_name in TEST_PACKAGES:
        package = repo.find_packages(package_name)[0]
        assert package == legacy_repo.find_packages(package_name)[0]
        assert package.source_type == "find_links"


def test_single_link():
    repo = MockRepository("http://foo.com/bar/relative/poetry-0.1.0-py3-none-any.whl")

    assert repo.single_link
    single_link = repo._get("poetry")
    assert isinstance(single_link, SingleLink)
    assert next(single_link.links) == Link(repo.full_url, single_link, None)

    pkg = repo.find_packages("poetry")[0]
    assert pkg.name == "poetry"
    assert pkg.version.text == "0.1.0"

    # make sure we don't find other packages
    assert repo.find_packages("isort") == []


def test_package():
    repo = MockRepository()
    legacy_repo = LegacyMockRepository()

    for package_name in TEST_PACKAGES:
        package = repo.find_packages(package_name)[0]
        assert repo.package(package.name, package.version.text) == legacy_repo.package(
            package.name, package.version.text
        )


def test_get_release_info():
    repo = MockRepository()
    legacy_repo = LegacyMockRepository()

    for package_name in TEST_PACKAGES:
        package = repo.find_packages(package_name)[0]
        assert repo.get_release_info(
            package_name, package.version.text
        ) == legacy_repo.get_release_info(package_name, package.version.text)
