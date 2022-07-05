from __future__ import annotations

import hashlib
import json

from pathlib import Path
from typing import TYPE_CHECKING

from poetry.installation.chooser import InvalidWheelName
from poetry.installation.chooser import Wheel


if TYPE_CHECKING:
    from poetry.core.packages.utils.link import Link

    from poetry.config.config import Config
    from poetry.utils.env import Env


class Chef:
    def __init__(self, config: Config, env: Env) -> None:
        self._env = env
        self._cache_dir = (
            Path(config.get("cache-dir")).expanduser().joinpath("artifacts")
        )

    def get_cached_archive_for_link(self, link: Link) -> Path | None:
        archives = self.get_cached_archives_for_link(link)
        if not archives:
            return None

        candidates: list[tuple[float | None, Path]] = []
        for archive in archives:
            if archive.suffix != ".whl":
                candidates.append((float("inf"), archive))
                continue

            try:
                wheel = Wheel(archive.name)
            except InvalidWheelName:
                continue

            if not wheel.is_supported_by_environment(self._env):
                continue

            candidates.append(
                (wheel.get_minimum_supported_index(self._env.supported_tags), archive),
            )

        if not candidates:
            return None

        return min(candidates)[1]

    def get_cached_archives_for_link(self, link: Link) -> list[Path]:
        cache_dir = self.get_cache_directory_for_link(link)

        archive_types = ["whl", "tar.gz", "tar.bz2", "bz2", "zip"]
        paths = []
        for archive_type in archive_types:
            for archive in cache_dir.glob(f"*.{archive_type}"):
                paths.append(Path(archive))

        return paths

    def get_cache_directory_for_link(self, link: Link) -> Path:
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
