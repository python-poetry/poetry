from __future__ import annotations

import urllib.parse
import warnings

from collections import defaultdict
from html import unescape
from typing import TYPE_CHECKING

from poetry.core.packages.utils.link import Link

from poetry.repositories.link_sources.base import LinkSource
from poetry.utils._compat import cached_property


if TYPE_CHECKING:
    from poetry.repositories.link_sources.base import LinkCache


with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import html5lib


class HTMLPage(LinkSource):
    def __init__(self, url: str, content: str) -> None:
        super().__init__(url=url)

        self._parsed = html5lib.parse(content, namespaceHTMLElements=False)

    @cached_property
    def _link_cache(self) -> LinkCache:
        links: LinkCache = defaultdict(lambda: defaultdict(list))
        for anchor in self._parsed.findall(".//a"):
            if anchor.get("href"):
                href = anchor.get("href")
                url = self.clean_link(urllib.parse.urljoin(self._url, href))
                pyrequire = anchor.get("data-requires-python")
                pyrequire = unescape(pyrequire) if pyrequire else None
                yanked_value = anchor.get("data-yanked")
                yanked: str | bool
                if yanked_value:
                    yanked = unescape(yanked_value)
                else:
                    yanked = "data-yanked" in anchor.attrib
                link = Link(url, requires_python=pyrequire, yanked=yanked)

                if link.ext not in self.SUPPORTED_FORMATS:
                    continue

                pkg = self.link_package_data(link)
                if pkg:
                    links[pkg.name][pkg.version].append(link)

        return links


class SimpleRepositoryPage(HTMLPage):
    def __init__(self, url: str, content: str) -> None:
        if not url.endswith("/"):
            url += "/"
        super().__init__(url=url, content=content)
