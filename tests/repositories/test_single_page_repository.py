from __future__ import annotations

import re

from pathlib import Path
from typing import TYPE_CHECKING

from poetry.core.packages.dependency import Dependency
from poetry.core.packages.utils.link import Link

from poetry.repositories.exceptions import PackageNotFound
from poetry.repositories.link_sources.html import SimpleRepositoryPage
from poetry.repositories.single_page_repository import SinglePageRepository


if TYPE_CHECKING:
    from packaging.utils import NormalizedName


class MockResponse:
    def __init__(self, url: str, content: str):
        self.url = url
        self.text = content


class MockSinglePageRepository(SinglePageRepository):
    FIXTURES = Path(__file__).parent / "fixtures" / "single-page"
    BASE_URL = "http://single-page.foo.bar"

    def __init__(self, page: str) -> None:
        super().__init__(
            "single-page",
            url=f"{self.BASE_URL}/{page}.html",
            disable_cache=True,
        )
        self._lazy_wheel = False

    def _get_response(self, endpoint: str):
        fixture = self.FIXTURES / self.url.rsplit("/", 1)[-1]
        if not fixture.exists():
            raise PackageNotFound(f"Package not found.")

        with fixture.open(encoding="utf-8") as f:
            return MockResponse(self._url, f.read())

    def _download(
        self, url: str, dest: Path, *, raise_accepts_ranges: bool = False
    ) -> None:
        raise RuntimeError("Tests are not configured for downloads")


def test_single_page_repository_get_page() -> None:
    repo = MockSinglePageRepository("jax_releases")

    page = repo.get_page("/ignored")
    links = list(page.links)

    assert len(links) == 21

    for link in links:
        assert re.match(r"^(jax|jaxlib)-0\.3\.\d.*\.(whl|tar\.gz)$", link.filename)
        assert link.netloc == "storage.googleapis.com"
        assert link.path.startswith("/jax-releases/")


def test_single_page_repository_find_packages() -> None:
    repo = MockSinglePageRepository("jax_releases")

    dep = Dependency("jaxlib", "0.3.7")

    packages = repo.find_packages(dep)

    assert len(packages) == 1

    package = packages[0]
    assert package.name == dep.name
    assert package.to_dependency().to_pep_508() == dep.to_pep_508()
