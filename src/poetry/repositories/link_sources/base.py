from __future__ import annotations

import logging
import re
import urllib.parse

from functools import cached_property
from typing import TYPE_CHECKING
from typing import ClassVar

from poetry.core.constraints.version import Version
from poetry.core.packages.package import Package
from poetry.core.version.exceptions import InvalidVersionError

from poetry.utils.patterns import sdist_file_re
from poetry.utils.patterns import wheel_file_re


if TYPE_CHECKING:
    from collections import defaultdict
    from collections.abc import Iterator

    from packaging.utils import NormalizedName
    from poetry.core.packages.utils.link import Link

    LinkCache = defaultdict[NormalizedName, defaultdict[Version, list[Link]]]


logger = logging.getLogger(__name__)


def make_absolute_url(url: str, base_url: str) -> str:
    """Makes a URL absolute by joining it with a base URL
    if it is not already absolute.
    """
    # This shortcut covers the absolute URL schemes commonly emitted by simple
    # repository pages. Other absolute forms still go through urljoin, which
    # preserves correct handling for protocol-relative URLs and uncommon schemes.
    if url.startswith(("http://", "https://", "file://")):
        return url
    return urllib.parse.urljoin(base_url, url)


class LinkSource:
    VERSION_REGEX = re.compile(r"(?i)([a-z0-9_\-.]+?)-(?=\d)([a-z0-9_.!+-]+)")
    CLEAN_REGEX = re.compile(r"[^a-z0-9$&+,/:;=?@.#%_\\|-]", re.I)
    SUPPORTED_FORMATS: ClassVar[list[str]] = [
        ".tar.gz",
        ".whl",
        ".zip",
        ".tar.bz2",
        ".tar.xz",
        ".tar.Z",
        ".tar",
    ]

    def __init__(self, url: str) -> None:
        self._url = url

    @property
    def url(self) -> str:
        return self._url

    def versions(self, name: NormalizedName) -> Iterator[Version]:
        yield from self._link_cache[name]

    @property
    def packages(self) -> Iterator[Package]:
        for link in self.links:
            pkg = self.link_package_data(link)

            if pkg:
                yield pkg

    @property
    def links(self) -> Iterator[Link]:
        for links_per_version in self._link_cache.values():
            for links in links_per_version.values():
                yield from links

    @classmethod
    def link_package_data(cls, link: Link) -> Package | None:
        name: str | None = None
        version_string: str | None = None
        version: Version | None = None
        m = wheel_file_re.match(link.filename) or sdist_file_re.match(link.filename)

        if m:
            name = m.group("name")
            version_string = m.group("ver")
        else:
            info, _ext = link.splitext()
            match = cls.VERSION_REGEX.match(info)
            if match:
                name = match.group(1)
                version_string = match.group(2)

        if version_string:
            try:
                version = Version.parse(version_string)
            except InvalidVersionError:
                logger.debug(
                    "Skipping url (%s) due to invalid version (%s)", link.url, version
                )
                return None

        pkg = None
        if name and version:
            pkg = Package(name, version, source_url=link.url)
        return pkg

    def links_for_version(
        self, name: NormalizedName, version: Version
    ) -> Iterator[Link]:
        yield from self._link_cache[name][version]

    def clean_link(self, url: str) -> str:
        """Makes sure a link is fully encoded.  That is, if a ' ' shows up in
        the link, it will be rewritten to %20 (while not over-quoting
        % or other characters)."""
        return self.CLEAN_REGEX.sub(lambda match: f"%{ord(match.group(0)):02x}", url)

    def yanked(self, name: NormalizedName, version: Version) -> str | bool:
        reasons = set()
        for link in self.links_for_version(name, version):
            if link.yanked:
                if link.yanked_reason:
                    reasons.add(link.yanked_reason)
            else:
                # release is not yanked if at least one file is not yanked
                return False
        # if all files are yanked (or there are no files) the release is yanked
        if reasons:
            return "\n".join(sorted(reasons))
        return True

    @cached_property
    def _link_cache(self) -> LinkCache:
        raise NotImplementedError()


class SimpleRepositoryRootPage:
    """
    This class represents the parsed content of a "simple" repository's root page.
    """

    def search(self, query: str | list[str]) -> list[str]:
        if isinstance(query, str):
            # performance shortcut
            # We could also create a list from query and use the more general code below,
            # but this is a common case that we can optimize for.
            return [name for name in self.package_names if query in name]

        return [
            name for name in self.package_names if any(token in name for token in query)
        ]

    @cached_property
    def package_names(self) -> list[str]:
        # should be overridden in subclasses
        return []
