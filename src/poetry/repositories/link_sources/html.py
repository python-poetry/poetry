from __future__ import annotations

import urllib.parse
import warnings

from html import unescape
from typing import TYPE_CHECKING

from poetry.core.packages.utils.link import Link

from poetry.repositories.link_sources.base import LinkSource


if TYPE_CHECKING:
    from collections.abc import Iterator

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import html5lib


class HTMLPage(LinkSource):
    def __init__(self, url: str, content: str) -> None:
        super().__init__(url=url)

        self._parsed = html5lib.parse(content, namespaceHTMLElements=False)

    @property
    def links(self) -> Iterator[Link]:
        for anchor in self._parsed.findall(".//a"):
            if anchor.get("href"):
                href = anchor.get("href")
                url = self.clean_link(urllib.parse.urljoin(self._url, href))
                pyrequire = anchor.get("data-requires-python")
                pyrequire = unescape(pyrequire) if pyrequire else None
                link = Link(url, self, requires_python=pyrequire)

                if link.ext not in self.SUPPORTED_FORMATS:
                    continue

                yield link


class SimpleRepositoryPage(HTMLPage):
    def __init__(self, url: str, content: str) -> None:
        if not url.endswith("/"):
            url += "/"
        super().__init__(url=url, content=content)


class SimpleIndexPage:
    """Describes the root page of a PEP503 compliant repository.

    This contains a list of links, each one corresponding to a served project.
    """

    def __init__(self, url: str, content: str) -> None:
        if not url.endswith("/"):
            url += "/"

        self._url = url
        self._content = content
        self._parsed = html5lib.parse(content, namespaceHTMLElements=False)
        self._cached_packages = set(self.links)

    @property
    def links(self) -> Iterator[Link]:
        # Note: PEP426 specifies that comparisons should be
        # case-insensitive. For simplicity, we'll do lookups using
        # lowercase-naming, and treating - and _ equivalently.
        for anchor in self._parsed.findall(".//a"):
            yield anchor.text.lower().replace("-", "_")

    def serves_package(self, name: str) -> bool:
        return name.lower().replace("-", "_") in self._cached_packages
