from __future__ import annotations

from collections import defaultdict
from functools import cached_property
from functools import partial
from typing import TYPE_CHECKING
from typing import Any

from poetry.core.packages.utils.link import Link
from poetry.core.packages.utils.utils import splitext

from poetry.repositories.link_sources.base import LinkSource
from poetry.repositories.link_sources.base import SimpleRepositoryRootPage
from poetry.repositories.link_sources.base import make_absolute_url


if TYPE_CHECKING:
    from poetry.repositories.link_sources.base import LinkFactoryCache


class SimpleJsonPage(LinkSource):
    """Links as returned by PEP 691 compatible JSON-based Simple API."""

    def __init__(self, url: str, content: dict[str, Any]) -> None:
        super().__init__(url=url)
        self.content = content

    @cached_property
    def _link_factory_cache(self) -> LinkFactoryCache:
        # Only the filename is needed to enumerate the available versions, so we
        # defer building the Link (and cleaning its URL) to _make_link, which is
        # only called when the version's links are actually retrieved. For large
        # projects this avoids constructing tens of thousands of Link objects
        # that are never used during resolution.
        links: LinkFactoryCache = defaultdict(lambda: defaultdict(list))
        for file in self.content["files"]:
            filename = file["filename"]
            if splitext(filename, is_filename=True)[1] not in self.SUPPORTED_FORMATS:
                continue

            name_and_version = self._link_package_name_and_version(filename)
            if name_and_version:
                name, version = name_and_version
                links[name][version].append(partial(self._make_link, file))

        return links

    def _make_link(self, file: dict[str, Any]) -> Link:
        url = self.clean_link(make_absolute_url(file["url"], self._url))

        # see https://peps.python.org/pep-0714/#clients
        # and https://peps.python.org/pep-0691/#project-detail
        metadata: dict[str, str] | bool = False
        for metadata_key in ("core-metadata", "dist-info-metadata"):
            if metadata_key in file:
                metadata_value = file[metadata_key]
                if metadata_value and isinstance(metadata_value, dict):
                    metadata = metadata_value
                else:
                    metadata = bool(metadata_value)
                break

        # use filename for performance (and strictly speaking also for correctness)
        return Link(
            url,
            filename=file["filename"],
            requires_python=file.get("requires-python"),
            hashes=file.get("hashes", {}),
            yanked=file.get("yanked", False),
            metadata=metadata,
            size=file.get("size"),
            upload_time=file.get("upload-time"),
        )


class SimpleRepositoryJsonRootPage(SimpleRepositoryRootPage):
    """
    This class represents the parsed content of the JSON version
    of a "simple" repository's root page.
    This follows the specification laid out in PEP 691.

    See: https://peps.python.org/pep-0691/
    """

    def __init__(self, content: dict[str, Any]) -> None:
        self._content = content

    @cached_property
    def package_names(self) -> list[str]:
        results: list[str] = []

        for project in self._content.get("projects", []):
            if name := project.get("name"):
                results.append(name)

        return results
