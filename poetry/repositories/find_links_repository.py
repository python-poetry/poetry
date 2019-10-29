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
    """Parse an url returning the base url for the repository and
    the name of any index page that will contain links"""
    url_parts = urlparse.urlparse(url)
    path = url_parts.path

    path = path.split("/")
    if "." in path[-1]:
        match = re.match(FilteredPage.VERSION_REGEX, path[-1])
        if match and any(fmt in path[-1] for fmt in FilteredPage.SUPPORTED_FORMATS):
            index_page = path[-1]
            single_link = True
        else:
            index_page = path[-1]
            single_link = False
        return (
            url_parts._replace(path="/".join(path[:-1])).geturl(),
            index_page,
            single_link,
        )
    else:
        return url_parts.geturl().rstrip("/"), "", False


class FilteredPage(Page):
    """A representation of a web page that presents links only for a
    particular package name."""

    VERSION_REGEX = re.compile(
        r"(?i)(?P<package_name>[a-z0-9_\-.]+?)-(?=\d)(?P<version>[a-z0-9_.!+-]+)"
    )

    def __init__(self, url, name, content, headers):
        self.name = name
        super(FilteredPage, self).__init__(url, content, headers)

    def _parse_url(self, url):  # type: (str) -> str
        parsed_url, self.index_page, self.single_link = parse_url(url)
        return parsed_url

    @property
    def links(self):  # type: () -> Generator[Link]
        for anchor in self._parsed.findall(".//a"):
            if anchor.get("href"):
                href = anchor.get("href")
                url = self.clean_link(urlparse.urljoin(self._url + "/", href))
                pyrequire = anchor.get("data-requires-python")
                pyrequire = unescape(pyrequire) if pyrequire else None

                url_parts = urlparse.urlparse(url)
                match = re.search(self.VERSION_REGEX, url_parts.path)
                if match is None or self.name != match.groupdict()["package_name"]:
                    continue

                link = Link(url, self, requires_python=pyrequire)

                if link.ext not in self.SUPPORTED_FORMATS:
                    continue

                yield link


class SingleLink(FilteredPage):
    def __init__(self, url, name):  # type: (str, str) -> None
        match = re.search(self.VERSION_REGEX, url)
        if match and name == match.groupdict()["package_name"]:
            self._link = [Link(url, self, None)]
        else:
            self._link = []

    @property
    def links(self):  # type: (str) -> Generator[Link]
        for link in self._link:
            yield link


class FindLinksRepository(LegacyRepository):
    repository_type = "find_links"

    def _parse_url(self, url):  # type: (str) -> str
        parsed_url, self.file_path, self.single_link = parse_url(url)
        return parsed_url

    def _get(self, name):  # type: (str) -> Union[Page, None]
        url = self.full_url
        if self.single_link:
            return SingleLink(url, name)

        response = self._session.get(url)
        if response.status_code == 404:
            return
        return FilteredPage(url, name, response.content, response.headers)

    @property
    def full_url(self):  # type: () -> str
        return self._url + "/" + self.file_path
