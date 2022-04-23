from __future__ import annotations

import contextlib
import re

from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Iterator

from poetry.core.packages.package import Package
from poetry.core.semver.version import Version

from poetry.utils.helpers import canonicalize_name
from poetry.utils.patterns import sdist_file_re
from poetry.utils.patterns import wheel_file_re


if TYPE_CHECKING:
    from poetry.core.packages.utils.link import Link


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

            if pkg.name == name and pkg.version and pkg.version not in seen:
                seen.add(pkg.version)
                yield pkg.version

    @property
    def packages(self) -> Iterator[Package]:
        for link in self.links:
            pkg = self.link_package_data(link)

            if pkg.name and pkg.version:
                yield pkg

    @property
    @abstractmethod
    def links(self) -> Iterator[Link]:
        raise NotImplementedError()

    def link_package_data(self, link: Link) -> Package:
        name, version = None, None
        m = wheel_file_re.match(link.filename) or sdist_file_re.match(link.filename)

        if m:
            name = canonicalize_name(m.group("name"))
            version_string = m.group("ver")
        else:
            info, ext = link.splitext()
            match = self.VERSION_REGEX.match(info)
            if match:
                version_string = match.group(2)

        with contextlib.suppress(ValueError):
            version = Version.parse(version_string)

        return Package(name, version, source_url=link.url)

    def links_for_version(self, name: str, version: Version) -> Iterator[Link]:
        name = canonicalize_name(name)

        for link in self.links:
            pkg = self.link_package_data(link)

            if pkg.name == name and pkg.version and pkg.version == version:
                yield link

    def clean_link(self, url: str) -> str:
        """Makes sure a link is fully encoded.  That is, if a ' ' shows up in
        the link, it will be rewritten to %20 (while not over-quoting
        % or other characters)."""
        return self.CLEAN_REGEX.sub(lambda match: f"%{ord(match.group(0)):02x}", url)
