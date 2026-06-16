from __future__ import annotations

import logging
import re
import urllib.parse

from functools import cached_property
from typing import TYPE_CHECKING
from typing import ClassVar

from packaging.utils import canonicalize_name
from poetry.core.constraints.version import Version
from poetry.core.packages.package import Package
from poetry.core.packages.utils.utils import splitext
from poetry.core.version.exceptions import InvalidVersionError

from poetry.utils.patterns import sdist_file_re
from poetry.utils.patterns import wheel_file_re


if TYPE_CHECKING:
    from collections import defaultdict
    from collections.abc import Callable
    from collections.abc import Iterator

    from packaging.utils import NormalizedName
    from poetry.core.packages.utils.link import Link

    # The cache stores factories that build a Link on demand, so that Links are
    # only constructed for the (few) versions actually retrieved rather than for
    # every file listed by the repository.
    LinkFactory = Callable[[], Link]
    LinkCache = defaultdict[NormalizedName, defaultdict[Version, list[LinkFactory]]]


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
            for link_factories in links_per_version.values():
                for make_link in link_factories:
                    yield make_link()

    @classmethod
    def _link_package_name_and_version(
        cls, filename: str
    ) -> tuple[NormalizedName, Version] | None:
        """Extract just the (normalized name, version) from a filename.

        This is the hot path used when building the link cache: it works on the
        filename alone so that the cache can be populated without constructing a
        `Link` (let alone a full `Package`) for every file. The `Link` for a
        given file is only built when its version is actually retrieved.
        """
        name: str | None = None
        version_string: str | None = None
        m = wheel_file_re.match(filename) or sdist_file_re.match(filename)

        if m:
            name = m.group("name")
            version_string = m.group("ver")
        else:
            info, _ext = splitext(filename, is_filename=True)
            match = cls.VERSION_REGEX.match(info)
            if match:
                name = match.group(1)
                version_string = match.group(2)

        if not (name and version_string):
            return None

        try:
            version = Version.parse(version_string)
        except InvalidVersionError:
            logger.debug(
                "Skipping file (%s) due to invalid version (%s)",
                filename,
                version_string,
            )
            return None

        return canonicalize_name(name), version

    @classmethod
    def link_package_data(cls, link: Link) -> Package | None:
        name_and_version = cls._link_package_name_and_version(link.filename)
        if name_and_version is None:
            return None

        name, version = name_and_version
        return Package(name, version, source_url=link.url)

    def links_for_version(
        self, name: NormalizedName, version: Version
    ) -> Iterator[Link]:
        for make_link in self._link_cache[name][version]:
            yield make_link()

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
