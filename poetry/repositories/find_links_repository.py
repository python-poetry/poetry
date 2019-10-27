import re

try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

try:
    from html import unescape
except ImportError:
    try:
        from html.parser import HTMLParser
    except ImportError:
        from HTMLParser import HTMLParser

    unescape = HTMLParser().unescape

from typing import Generator
from typing import Tuple
from typing import Union


from poetry.packages.utils.link import Link

from .legacy_repository import LegacyRepository, Page


def parse_url(url):  # type: (str) -> Tuple[str, str]
    """"""
    url_parts = urlparse.urlparse(url)
    path = url_parts.path

    path = path.split("/")
    if "." in path[-1]:
        index_page = path[-1]
        return url_parts._replace(path="/".join(path[:-1])).geturl(), index_page


class FilteredPage(Page):
    """A representation of a web page that presents links only for a
    particular package name."""

    VERSION_REGEX = re.compile(
        r"(?i)(?P<package_name>[a-z0-9_\-.]+?)-(?=\d)(?P<version>[a-z0-9_.!+-]+)"
    )

    def __init__(self, url, name, content, headers):
        self.name = name
        super().__init__(url, content, headers)

    def _parse_url(self, url):  # type: (str) -> str
        parsed_url, self.index_page = parse_url(url)
        return parsed_url

    @property
    def links(self):  # type: () -> Generator[Link]
        for anchor in self._parsed.findall(".//a"):
            if anchor.get("href"):
                href = anchor.get("href")
                url = self.clean_link(urlparse.urljoin(self._url, href))
                pyrequire = anchor.get("data-requires-python")
                pyrequire = unescape(pyrequire) if pyrequire else None

                url_parts = urlparse.urlparse(url)
                match = re.search(self.VERSION_REGEX, url_parts.path)
                if self.name != match.groupdict()["package_name"]:
                    continue

                link = Link(url, self, requires_python=pyrequire)

                if link.ext not in self.SUPPORTED_FORMATS:
                    continue

                yield link


class FindLinksRepository(LegacyRepository):
    repository_type = "find_links"

    def _parse_url(self, url):  # type: (str) -> str
        parsed_url, self.index_page = parse_url(url)
        return parsed_url

    def _get(self, name):  # type: (str) -> Union[Page, None]
        url = self._url + "/" + self.index_page
        response = self._session.get(url)
        if response.status_code == 404:
            return

        return FilteredPage(url, name, response.content, response.headers)
