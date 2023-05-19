from __future__ import annotations

from collections import defaultdict
from functools import cached_property
from typing import TYPE_CHECKING
from typing import Any

from poetry.core.packages.utils.link import Link

from poetry.repositories.link_sources.base import LinkSource


if TYPE_CHECKING:
    from poetry.repositories.link_sources.base import LinkCache


class SimpleJsonPage(LinkSource):
    """Links as returned by PEP 691 compatible JSON-based Simple API."""

    def __init__(self, url: str, content: dict[str, Any]) -> None:
        super().__init__(url=url)
        self.content = content

    @cached_property
    def _link_cache(self) -> LinkCache:
        links: LinkCache = defaultdict(lambda: defaultdict(list))
        for file in self.content["files"]:
            url = file["url"]
            requires_python = file.get("requires-python")
            yanked = file.get("yanked", False)
            link = Link(url, requires_python=requires_python, yanked=yanked)

            if link.ext not in self.SUPPORTED_FORMATS:
                continue

            pkg = self.link_package_data(link)
            if pkg:
                links[pkg.name][pkg.version].append(link)

        return links
