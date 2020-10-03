import re

from typing import List
from typing import Tuple

from packaging.tags import Tag

from poetry.core.packages.package import Package
from poetry.core.packages.utils.link import Link
from poetry.repositories.pool import Pool
from poetry.utils.env import Env
from poetry.utils.patterns import wheel_file_re


class InvalidWheelName(Exception):
    pass


class Wheel(object):
    def __init__(self, filename):  # type: (str) -> None
        wheel_info = wheel_file_re.match(filename)
        if not wheel_info:
            raise InvalidWheelName("{} is not a valid wheel filename.".format(filename))

        self.filename = filename
        self.name = wheel_info.group("name").replace("_", "-")
        self.version = wheel_info.group("ver").replace("_", "-")
        self.build_tag = wheel_info.group("build")
        self.pyversions = wheel_info.group("pyver").split(".")
        self.abis = wheel_info.group("abi").split(".")
        self.plats = wheel_info.group("plat").split(".")

        self.tags = {
            Tag(x, y, z) for x in self.pyversions for y in self.abis for z in self.plats
        }

    def get_minimum_supported_index(self, tags):
        indexes = [tags.index(t) for t in self.tags if t in tags]

        return min(indexes) if indexes else None

    def is_supported_by_environment(self, env):
        return bool(set(env.supported_tags).intersection(self.tags))


class Chooser:
    """
    A Chooser chooses an appropriate release archive for packages.
    """

    def __init__(self, pool, env):  # type: (Pool, Env) -> None
        self._pool = pool
        self._env = env

    def choose_for(self, package):  # type: (Package) -> Link
        """
        Return the url of the selected archive for a given package.
        """
        links = []
        for link in self._get_links(package):
            if link.is_wheel and not Wheel(link.filename).is_supported_by_environment(
                self._env
            ):
                continue

            if link.ext in {".egg", ".exe", ".msi", ".rpm", ".srpm"}:
                continue

            links.append(link)

        if not links:
            raise RuntimeError(
                "Unable to find installation candidates for {}".format(package)
            )

        # Get the best link
        chosen = max(links, key=lambda link: self._sort_key(package, link))
        if not chosen:
            raise RuntimeError(
                "Unable to find installation candidates for {}".format(package)
            )

        return chosen

    def _get_links(self, package):  # type: (Package) -> List[Link]
        if not package.source_type:
            if not self._pool.has_repository("pypi"):
                repository = self._pool.repositories[0]
            else:
                repository = self._pool.repository("pypi")
        else:
            repository = self._pool.repository(package.source_reference)

        links = repository.find_links_for_package(package)

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

    def _sort_key(self, package, link):  # type: (Package, Link) -> Tuple
        """
        Function to pass as the `key` argument to a call to sorted() to sort
        InstallationCandidates by preference.
        Returns a tuple such that tuples sorting as greater using Python's
        default comparison operator are more preferred.
        The preference is as follows:
        First and foremost, candidates with allowed (matching) hashes are
        always preferred over candidates without matching hashes. This is
        because e.g. if the only candidate with an allowed hash is yanked,
        we still want to use that candidate.
        Second, excepting hash considerations, candidates that have been
        yanked (in the sense of PEP 592) are always less preferred than
        candidates that haven't been yanked. Then:
        If not finding wheels, they are sorted by version only.
        If finding wheels, then the sort order is by version, then:
          1. existing installs
          2. wheels ordered via Wheel.support_index_min(self._supported_tags)
          3. source archives
        If prefer_binary was set, then all wheels are sorted above sources.
        Note: it was considered to embed this logic into the Link
              comparison operators, but then different sdist links
              with the same version, would have to be considered equal
        """
        support_num = len(self._env.supported_tags)
        build_tag = ()
        binary_preference = 0
        if link.is_wheel:
            wheel = Wheel(link.filename)
            if not wheel.is_supported_by_environment(self._env):
                raise RuntimeError(
                    "{} is not a supported wheel for this platform. It "
                    "can't be sorted.".format(wheel.filename)
                )

            # TODO: Binary preference
            pri = -(wheel.get_minimum_supported_index(self._env.supported_tags))
            if wheel.build_tag is not None:
                match = re.match(r"^(\d+)(.*)$", wheel.build_tag)
                build_tag_groups = match.groups()
                build_tag = (int(build_tag_groups[0]), build_tag_groups[1])
        else:  # sdist
            pri = -support_num

        has_allowed_hash = int(self._is_link_hash_allowed_for_package(link, package))

        # TODO: Proper yank value
        yank_value = 0

        return (
            has_allowed_hash,
            yank_value,
            binary_preference,
            package.version,
            build_tag,
            pri,
        )

    def _is_link_hash_allowed_for_package(
        self, link, package
    ):  # type: (Link, Package) -> bool
        if not link.hash:
            return True

        h = link.hash_name + ":" + link.hash

        return h in {f["hash"] for f in package.files}
