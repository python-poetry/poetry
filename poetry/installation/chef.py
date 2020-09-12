import hashlib
import json

from typing import TYPE_CHECKING

from poetry.core.packages.utils.link import Link
from poetry.utils._compat import Path

from .chooser import InvalidWheelName
from .chooser import Wheel


if TYPE_CHECKING:
    from typing import List
    from typing import Optional

    from poetry.config.config import Config
    from poetry.utils.env import Env


class Chef:
    def __init__(self, config, env):  # type: (Config, Env) -> None
        self._config = config
        self._env = env
        self._cache_dir = (
            Path(config.get("cache-dir")).expanduser().joinpath("artifacts")
        )

    def prepare(self, archive):  # type: (Path) -> Path
        return archive

    def prepare_sdist(self, archive):  # type: (Path) -> Path
        return archive

    def prepare_wheel(self, archive):  # type: (Path) -> Path
        return archive

    def should_prepare(self, archive):  # type: (Path) -> bool
        return not self.is_wheel(archive)

    def is_wheel(self, archive):  # type: (Path) -> bool
        return archive.suffix == ".whl"

    def get_cached_archive_for_link(self, link):  # type: (Link) -> Optional[Link]
        # If the archive is already a wheel, there is no need to cache it.
        if link.is_wheel:
            pass

        archives = self.get_cached_archives_for_link(link)

        if not archives:
            return link

        candidates = []
        for archive in archives:
            if not archive.is_wheel:
                candidates.append((float("inf"), archive))
                continue

            try:
                wheel = Wheel(archive.filename)
            except InvalidWheelName:
                continue

            if not wheel.is_supported_by_environment(self._env):
                continue

            candidates.append(
                (wheel.get_minimum_supported_index(self._env.supported_tags), archive),
            )

        if not candidates:
            return link

        return min(candidates)[1]

    def get_cached_archives_for_link(self, link):  # type: (Link) -> List[Link]
        cache_dir = self.get_cache_directory_for_link(link)

        archive_types = ["whl", "tar.gz", "tar.bz2", "bz2", "zip"]
        links = []
        for archive_type in archive_types:
            for archive in cache_dir.glob("*.{}".format(archive_type)):
                links.append(Link(archive.as_uri()))

        return links

    def get_cache_directory_for_link(self, link):  # type: (Link) -> Path
        key_parts = {"url": link.url_without_fragment}

        if link.hash_name is not None and link.hash is not None:
            key_parts[link.hash_name] = link.hash

        if link.subdirectory_fragment:
            key_parts["subdirectory"] = link.subdirectory_fragment

        key_parts["interpreter_name"] = self._env.marker_env["interpreter_name"]
        key_parts["interpreter_version"] = "".join(
            self._env.marker_env["interpreter_version"].split(".")[:2]
        )

        key = hashlib.sha256(
            json.dumps(
                key_parts, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("ascii")
        ).hexdigest()

        split_key = [key[:2], key[2:4], key[4:6], key[6:]]

        return self._cache_dir.joinpath(*split_key)
