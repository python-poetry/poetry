from __future__ import annotations

import contextlib
import hashlib
import os
import urllib

from abc import ABC
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote

import requests
import requests.auth

from cachecontrol import CacheControl
from packaging.tags import Tag
from packaging.tags import sys_tags
from poetry.core.packages.dependency import Dependency
from poetry.core.packages.utils.link import Link
from poetry.core.version.markers import parse_marker

from poetry.config.config import Config
from poetry.repositories.cached import CachedRepository
from poetry.repositories.exceptions import PackageNotFound
from poetry.repositories.exceptions import RepositoryError
from poetry.repositories.link_sources.html import HTMLPage
from poetry.utils.authenticator import Authenticator
from poetry.utils.helpers import download_file
from poetry.utils.helpers import temporary_directory
from poetry.utils.patterns import wheel_file_re


if TYPE_CHECKING:
    from poetry.inspection.info import PackageInfo


class HTTPRepository(CachedRepository, ABC):
    def __init__(
        self,
        name: str,
        url: str,
        config: Config | None = None,
        disable_cache: bool = False,
        cert: Path | None = None,
        client_cert: Path | None = None,
    ) -> None:
        super().__init__(name, "_http", disable_cache)
        self._url = url
        self._client_cert = client_cert
        self._cert = cert

        self._authenticator = Authenticator(
            config=config or Config(use_environment=True)
        )

        self._session = CacheControl(
            self._authenticator.session, cache=self._cache_control_cache
        )

        username, password = self._authenticator.get_credentials_for_url(self._url)
        if username is not None and password is not None:
            self._authenticator.session.auth = requests.auth.HTTPBasicAuth(
                username, password
            )

        if self._cert:
            self._authenticator.session.verify = str(self._cert)

        if self._client_cert:
            self._authenticator.session.cert = str(self._client_cert)

    @property
    def session(self) -> CacheControl:
        return self._session

    def __del__(self) -> None:
        with contextlib.suppress(AttributeError):
            self._session.close()

    @property
    def url(self) -> str:
        return self._url

    @property
    def cert(self) -> Path | None:
        return self._cert

    @property
    def client_cert(self) -> Path | None:
        return self._client_cert

    @property
    def authenticated_url(self) -> str:
        if not self._session.auth:
            return self.url

        parsed = urllib.parse.urlparse(self.url)
        username = quote(self._session.auth.username, safe="")
        password = quote(self._session.auth.password, safe="")

        return f"{parsed.scheme}://{username}:{password}@{parsed.netloc}{parsed.path}"

    def _download(self, url: str, dest: str) -> None:
        return download_file(url, dest, session=self.session)

    def _get_info_from_wheel(self, url: str) -> PackageInfo:
        from poetry.inspection.info import PackageInfo

        wheel_name = urllib.parse.urlparse(url).path.rsplit("/")[-1]
        self._log(f"Downloading wheel: {wheel_name}", level="debug")

        filename = os.path.basename(wheel_name)

        with temporary_directory() as temp_dir:
            filepath = Path(temp_dir) / filename
            self._download(url, str(filepath))

            return PackageInfo.from_wheel(filepath)

    def _get_info_from_sdist(self, url: str) -> PackageInfo:
        from poetry.inspection.info import PackageInfo

        sdist_name = urllib.parse.urlparse(url).path
        sdist_name_log = sdist_name.rsplit("/")[-1]

        self._log(f"Downloading sdist: {sdist_name_log}", level="debug")

        filename = os.path.basename(sdist_name)

        with temporary_directory() as temp_dir:
            filepath = Path(temp_dir) / filename
            self._download(url, str(filepath))

            return PackageInfo.from_sdist(filepath)

    def _get_info_from_urls(self, urls: dict[str, list[str]]) -> PackageInfo:
        # Checking wheels first as they are more likely to hold
        # the necessary information
        if "bdist_wheel" in urls:
            # Check for a universal wheel
            wheels = urls["bdist_wheel"]

            universal_wheel = None
            universal_python2_wheel = None
            universal_python3_wheel = None
            platform_specific_wheels = {}
            for wheel in wheels:
                link = Link(wheel)
                m = wheel_file_re.match(link.filename)
                if not m:
                    continue

                pyver = m.group("pyver")
                abi = m.group("abi")
                plat = m.group("plat")
                if abi == "none" and plat == "any":
                    # Universal wheel
                    if pyver == "py2.py3":
                        # Any Python
                        universal_wheel = wheel
                    elif pyver == "py2":
                        universal_python2_wheel = wheel
                    else:
                        universal_python3_wheel = wheel
                else:
                    platform_specific_wheels[Tag(pyver, abi, plat)] = wheel

            if universal_wheel is not None:
                return self._get_info_from_wheel(universal_wheel)

            info = None
            if universal_python2_wheel and universal_python3_wheel:
                info = self._get_info_from_wheel(universal_python2_wheel)

                py3_info = self._get_info_from_wheel(universal_python3_wheel)
                if py3_info.requires_dist:
                    if not info.requires_dist:
                        info.requires_dist = py3_info.requires_dist

                        return info

                    py2_requires_dist = {
                        Dependency.create_from_pep_508(r).to_pep_508()
                        for r in info.requires_dist
                    }
                    py3_requires_dist = {
                        Dependency.create_from_pep_508(r).to_pep_508()
                        for r in py3_info.requires_dist
                    }
                    base_requires_dist = py2_requires_dist & py3_requires_dist
                    py2_only_requires_dist = py2_requires_dist - py3_requires_dist
                    py3_only_requires_dist = py3_requires_dist - py2_requires_dist

                    # Normalizing requires_dist
                    requires_dist = list(base_requires_dist)
                    for requirement in py2_only_requires_dist:
                        dep = Dependency.create_from_pep_508(requirement)
                        dep.marker = dep.marker.intersect(
                            parse_marker("python_version == '2.7'")
                        )
                        requires_dist.append(dep.to_pep_508())

                    for requirement in py3_only_requires_dist:
                        dep = Dependency.create_from_pep_508(requirement)
                        dep.marker = dep.marker.intersect(
                            parse_marker("python_version >= '3'")
                        )
                        requires_dist.append(dep.to_pep_508())

                    info.requires_dist = sorted(set(requires_dist))

            if info:
                return info

            # Prefer non platform specific wheels
            if universal_python3_wheel:
                return self._get_info_from_wheel(universal_python3_wheel)

            if universal_python2_wheel:
                return self._get_info_from_wheel(universal_python2_wheel)

            # Prefer compatible platform wheel over sdist
            for tag in sys_tags():
                if tag in platform_specific_wheels:
                    return self._get_info_from_wheel(platform_specific_wheels[tag])

            if platform_specific_wheels and "sdist" not in urls:
                # Pick the first wheel available and hope for the best
                return self._get_info_from_wheel(
                    next(iter(platform_specific_wheels.values()))
                )

        return self._get_info_from_sdist(urls["sdist"][0])

    def _links_to_data(self, links: list[Link], data: PackageInfo) -> dict:
        if not links:
            raise PackageNotFound(
                f'No valid distribution links found for package: "{data.name}" version:'
                f' "{data.version}"'
            )
        urls = defaultdict(list)
        files = []
        for link in links:
            if link.is_wheel:
                urls["bdist_wheel"].append(link.url)
            elif link.filename.endswith(
                (".tar.gz", ".zip", ".bz2", ".xz", ".Z", ".tar")
            ):
                urls["sdist"].append(link.url)

            file_hash = f"{link.hash_name}:{link.hash}" if link.hash else None

            if not link.hash or (
                link.hash_name not in ("sha256", "sha384", "sha512")
                and hasattr(hashlib, link.hash_name)
            ):
                with temporary_directory() as temp_dir:
                    filepath = Path(temp_dir) / link.filename
                    self._download(link.url, str(filepath))

                    known_hash = (
                        getattr(hashlib, link.hash_name)() if link.hash_name else None
                    )
                    required_hash = hashlib.sha256()

                    chunksize = 4096
                    with filepath.open("rb") as f:
                        while True:
                            chunk = f.read(chunksize)
                            if not chunk:
                                break
                            if known_hash:
                                known_hash.update(chunk)
                            required_hash.update(chunk)

                    if not known_hash or known_hash.hexdigest() == link.hash:
                        file_hash = f"{required_hash.name}:{required_hash.hexdigest()}"

            files.append({"file": link.filename, "hash": file_hash})

        data.files = files

        info = self._get_info_from_urls(urls)

        data.summary = info.summary
        data.requires_dist = info.requires_dist
        data.requires_python = info.requires_python

        return data.asdict()

    def _get_response(self, endpoint: str) -> requests.Response | None:
        url = self._url + endpoint
        try:
            response = self.session.get(url)
            if response.status_code in (401, 403):
                self._log(
                    f"Authorization error accessing {url}",
                    level="warning",
                )
                return None
            if response.status_code == 404:
                return None
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise RepositoryError(e)

        if response.url != url:
            self._log(
                f"Response URL {response.url} differs from request URL {url}",
                level="debug",
            )
        return response

    def _get_page(self, endpoint: str) -> HTMLPage | None:
        response = self._get_response(endpoint)
        if not response:
            return None
        return HTMLPage(response.url, response.text)
