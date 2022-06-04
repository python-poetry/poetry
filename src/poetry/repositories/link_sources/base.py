from __future__ import annotations

import logging
import re

from abc import abstractmethod
from typing import TYPE_CHECKING

from poetry.core.packages.package import Package
from poetry.core.semver.version import Version

from poetry.utils.helpers import canonicalize_name
from poetry.utils.patterns import sdist_file_re
from poetry.utils.patterns import wheel_file_re


if TYPE_CHECKING:
    from collections.abc import Iterator

    from poetry.core.packages.utils.link import Link


logger = logging.getLogger(__name__)


class LinkSource:
    VERSION_REGEX = re.compile(r"(?i)([a-z0-9_\-.]+?)-(?=\d)([a-z0-9_.!+-]+)")
    CLEAN_REGEX = re.compile(r"[^a-z0-9$&+,/:;=?@.#%_\\|-]", re.I)
    SUPPORTED_FORMATS = [
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

    def versions(self, name: str) -> Iterator[Version]:
        name = canonicalize_name(name)
        seen: set[Version] = set()

        for link in self.links:
            pkg = self.link_package_data(link)

            if pkg and pkg.name == name and pkg.version not in seen:
                seen.add(pkg.version)
                yield pkg.version

    @property
    def packages(self) -> Iterator[Package]:
        for link in self.links:
            pkg = self.link_package_data(link)

            if pkg:
                yield pkg

    @property
    @abstractmethod
    def links(self) -> Iterator[Link]:
        raise NotImplementedError()

    @classmethod
    def link_package_data(cls, link: Link) -> Package | None:
        name, version_string, version = None, None, None
        m = wheel_file_re.match(link.filename) or sdist_file_re.match(link.filename)

        if m:
            name = canonicalize_name(m.group("name"))
            version_string = m.group("ver")
        else:
            info, ext = link.splitext()
            match = cls.VERSION_REGEX.match(info)
            if match:
                name = match.group(1)
                version_string = match.group(2)

        if version_string:
            try:
                version = Version.parse(version_string)
            except ValueError:
                logger.debug(
                    "Skipping url (%s) due to invalid version (%s)", link.url, version
                )
                return None

        pkg = None
        if name and version:
            pkg = Package(name, version, source_url=link.url)
        return pkg

    def links_for_version(self, name: str, version: Version) -> Iterator[Link]:
        name = canonicalize_name(name)

        for link in self.links:
            pkg = self.link_package_data(link)

            if pkg and pkg.name == name and pkg.version == version:
                yield link

    def clean_link(self, url: str) -> str:
        """Makes sure a link is fully encoded.  That is, if a ' ' shows up in
        the link, it will be rewritten to %20 (while not over-quoting
        % or other characters)."""
        return self.CLEAN_REGEX.sub(lambda match: f"%{ord(match.group(0)):02x}", url)
