import re

from typing import List
from typing import Tuple

from poetry.core.packages.package import Package
from poetry.core.packages.utils.link import Link
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.repositories.pypi_repository import PyPiRepository
from poetry.utils.env import Env
from poetry.utils.patterns import wheel_file_re


class Wheel(object):
    def __init__(self, filename):  # type: (str) -> None
        """
        :raises InvalidWheelFilename: when the filename is invalid for a wheel
        """
        wheel_info = wheel_file_re.match(filename)
        if not wheel_info:
            raise ValueError("{} is not a valid wheel filename.".format(filename))
        self.filename = filename
        self.name = wheel_info.group("name").replace("_", "-")
        self.version = wheel_info.group("ver").replace("_", "-")
        self.build_tag = wheel_info.group("build")
        self.pyversions = wheel_info.group("pyver").split(".")
        self.abis = wheel_info.group("abi").split(".")
        self.plats = wheel_info.group("plat").split(".")

        # All the tag combinations from this file
        self.file_tags = {
            (x, y, z) for x in self.pyversions for y in self.abis for z in self.plats
        }

    def support_index_min(self, tags):
        """
        Return the lowest index that one of the wheel's file_tag combinations
        achieves in the supported_tags list e.g. if there are 8 supported tags,
        and one of the file tags is first in the list, then return 0.  Returns
        None is the wheel is not supported.
        """
        indexes = [tags.index(c) for c in self.file_tags if c in tags]

        return min(indexes) if indexes else None

    def is_supported(self, tags):
        return bool(set(tags).intersection(self.file_tags))


class Chooser:
    """
    A Chooser chooses an appropriate release archive for packages.
    """

    def __init__(self, env):  # type: (Env) -> None
        self._env = env

    def choose_for(self, package):  # type: (Package) -> Link
        """
        Return the url of the selected archive for a given package.
        """
        links = []
        for link in self._get_links(package):
            if link.is_wheel and not Wheel(link.filename).is_supported(
                self._env.supported_tags
            ):
                continue

            links.append(link)

        if not links:
            raise RuntimeError(
                "Unable to find installation candidates for {}".format(package)
            )

        # Get the best link
        chosen = max(links, key=lambda link: self._link_sort_key(package, link))
        if not chosen:
            raise RuntimeError(
                "Unable to find installation candidates for {}".format(package)
            )

        return chosen

    def _get_links(self, package):  # type: (Package) -> List[Link]
        if not package.source_type:
            links = self._get_links_from_pypi(package)
        else:
            links = self._get_links_from_legacy(package)

        hashes = [f["hash"] for f in package.files]
        if not hashes:
            return links

        selected_links = []
        for link in links:
            if not link.hash:
                selected_links.append(link)
                continue

            h = link.hash_name + ":" + link.hash
            if h not in hashes:
                continue

            selected_links.append(link)

        return selected_links

    def _get_links_from_pypi(self, package):  # type: (Package) -> List[Link]
        repository = PyPiRepository(fallback=False)
        json_data = repository._get(
            "pypi/{}/{}/json".format(package.name, package.version)
        )
        if json_data is None:
            return []

        return [Link(url["url"]) for url in json_data["urls"]]

    def _get_links_from_legacy(self, package):  # type: (Package) -> List[Link]
        repository = LegacyRepository(package.source_reference, package.source_url)
        page = repository._get("/{}/".format(package.name.replace(".", "-")))
        if page is None:
            return []

        return list(page.links_for_version(package.version))

    def _link_sort_key(self, package, link):  # type: (Package, Link) -> Tuple
        """
        Function used to generate link sort key for link tuples.
        The greater the return value, the more preferred it is.
        If not finding wheels, then sorted by version only.
        If finding wheels, then the sort order is by version, then:
          1. existing installs
          2. wheels ordered via Wheel.support_index_min(self.valid_tags)
          3. source archives
        If prefer_binary was set, then all wheels are sorted above sources.
        Note: it was considered to embed this logic into the Link
              comparison operators, but then different sdist links
              with the same version, would have to be considered equal
        """
        support_num = len(self._env.supported_tags)
        build_tag = tuple()
        binary_preference = 0
        if link.is_wheel:
            wheel = Wheel(link.filename)
            # TODO: prefer binary
            pri = -(wheel.support_index_min(self._env.supported_tags))
            if wheel.build_tag is not None:
                match = re.match(r"^(\d+)(.*)$", wheel.build_tag)
                build_tag_groups = match.groups()
                build_tag = (int(build_tag_groups[0]), build_tag_groups[1])
        else:  # sdist
            pri = -support_num

        return binary_preference, package.version, build_tag, pri
