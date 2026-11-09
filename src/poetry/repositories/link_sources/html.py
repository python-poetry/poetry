from __future__ import annotations

from collections import defaultdict
from functools import cached_property
from html import unescape
from typing import TYPE_CHECKING

from poetry.core.packages.utils.link import Link

from poetry.repositories.link_sources.base import LinkSource
from poetry.repositories.link_sources.base import SimpleRepositoryRootPage
from poetry.repositories.link_sources.base import make_absolute_url
from poetry.repositories.parsers.html_page_parser import HTMLPageParser


if TYPE_CHECKING:
    from poetry.repositories.link_sources.base import LinkFactory
    from poetry.repositories.link_sources.base import LinkFactoryCache


def _const_factory(link: Link) -> LinkFactory:
    """Wrap an already-built link in a factory for the link cache."""
    return lambda: link


class HTMLPage(LinkSource):
    def __init__(self, url: str, content: str) -> None:
        super().__init__(url=url)

        parser = HTMLPageParser()
        parser.feed(content)
        self._parsed = parser.anchors
        self._base_url: str | None = parser.base_url

    @cached_property
    def _link_factory_cache(self) -> LinkFactoryCache:
        links: LinkFactoryCache = defaultdict(lambda: defaultdict(list))
        base_url = self._base_url or self._url
        for anchor in self._parsed:
            if href := anchor.get("href"):
                url = self.clean_link(make_absolute_url(href, base_url))
                pyrequire = anchor.get("data-requires-python")
                pyrequire = unescape(pyrequire) if pyrequire else None
                yanked_value = anchor.get("data-yanked")
                yanked: str | bool
                if yanked_value:
                    yanked = unescape(yanked_value)
                else:
                    yanked = "data-yanked" in anchor

                # see https://peps.python.org/pep-0714/#clients
                # and https://peps.python.org/pep-0658/#specification
                metadata: str | bool
                for metadata_key in ("data-core-metadata", "data-dist-info-metadata"):
                    metadata_value = anchor.get(metadata_key)
                    if metadata_value:
                        metadata = unescape(metadata_value)
                    else:
                        metadata = metadata_key in anchor
                    if metadata:
                        break
                link = Link(
                    url, requires_python=pyrequire, yanked=yanked, metadata=metadata
                )

                if link.ext not in self.SUPPORTED_FORMATS:
                    continue

                # The HTML API has no separate filename field, so the filename
                # (needed to parse name and version) has to be derived from the
                # URL, which means the Link is built eagerly here. The cache
                # stores factories, so it is wrapped in one that just returns it.
                name_and_version = self._link_package_name_and_version(link.filename)
                if name_and_version:
                    name, version = name_and_version
                    links[name][version].append(_const_factory(link))

        return links


class SimpleRepositoryHTMLRootPage(SimpleRepositoryRootPage):
    """
    This class represents the parsed content of the HTML version
    of a "simple" repository's root page.
    This follows the specification laid out in PEP 503.

    See: https://peps.python.org/pep-0503/
    """

    def __init__(self, content: str | None = None) -> None:
        parser = HTMLPageParser()
        parser.feed(content or "")
        self._parsed = parser.anchors

    @cached_property
    def package_names(self) -> list[str]:
        results: list[str] = []

        for anchor in self._parsed:
            if href := anchor.get("href"):
                results.append(href.rstrip("/"))

        return results
