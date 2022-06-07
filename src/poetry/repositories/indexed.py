from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.core.packages.package import Package

from poetry.repositories.exceptions import RepositoryError
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.repositories.link_sources.html import SimpleIndexPage


if TYPE_CHECKING:
    from poetry.core.packages.dependency import Dependency

    from poetry.config.config import Config


class IndexedLegacyRepository(LegacyRepository):
    def __init__(
        self,
        name: str,
        url: str,
        config: Config | None = None,
        disable_cache: bool = False,
    ) -> None:
        super().__init__(name, url.rstrip("/"), config, disable_cache)

        self._index_page = self._get_index_page()

    def find_packages(self, dependency: Dependency) -> list[Package]:
        if not self._index_page.serves_package(dependency.name):
            return []

        return super().find_packages(dependency)

    def _get_index_page(self) -> SimpleIndexPage:
        response = self._get_response("")
        if not response:
            raise RepositoryError(
                f"Failed fetching index page for repository {self.name}"
            )
        return SimpleIndexPage(response.url, response.text)
