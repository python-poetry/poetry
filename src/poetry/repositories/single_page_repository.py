from __future__ import annotations

from poetry.repositories.legacy_repository import LegacyRepository
from poetry.repositories.link_sources.html import SimpleRepositoryPage


class SinglePageRepository(LegacyRepository):
    def _get_page(self, endpoint: str | None = None) -> SimpleRepositoryPage | None:
        """
        Single page repositories only have one page irrespective of endpoint.
        """
        response = self._get_response("")
        if not response:
            return None
        return SimpleRepositoryPage(response.url, response.text)
