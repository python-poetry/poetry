import logging
import os
import tarfile
import zipfile

import pkginfo

from bz2 import BZ2File
from collections import defaultdict
from gzip import GzipFile
from typing import Dict
from typing import List
from typing import Union

try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

try:
    from xmlrpc.client import ServerProxy
except ImportError:
    from xmlrpclib import ServerProxy

from cachecontrol import CacheControl
from cachecontrol.caches.file_cache import FileCache
from cachy import CacheManager
from requests import get
from requests import session

from poetry.locations import CACHE_DIR
from poetry.packages import dependency_from_pep_508
from poetry.packages import Package
from poetry.packages.utils.link import Link
from poetry.semver import parse_constraint
from poetry.semver import VersionConstraint
from poetry.semver import VersionRange
from poetry.semver.exceptions import ParseVersionError
from poetry.utils._compat import Path
from poetry.utils._compat import to_str
from poetry.utils.helpers import parse_requires
from poetry.utils.helpers import temporary_directory
from poetry.utils.patterns import wheel_file_re
from poetry.utils.setup_reader import SetupReader
from poetry.version.markers import InvalidMarker
from poetry.version.markers import parse_marker

from .exceptions import PackageNotFound
from .repository import Repository


logger = logging.getLogger(__name__)


class PyPiRepository(Repository):

    CACHE_VERSION = parse_constraint("0.12.0")

    def __init__(self, url="https://pypi.org/", disable_cache=False, fallback=True):
        self._name = "PyPI"
        self._url = url
        self._disable_cache = disable_cache
        self._fallback = fallback

        release_cache_dir = Path(CACHE_DIR) / "cache" / "repositories" / "pypi"
        self._cache = CacheManager(
            {
                "default": "releases",
                "serializer": "json",
                "stores": {
                    "releases": {"driver": "file", "path": str(release_cache_dir)},
                    "packages": {"driver": "dict"},
                },
            }
        )

        self._session = CacheControl(
            session(), cache=FileCache(str(release_cache_dir / "_http"))
        )

        super(PyPiRepository, self).__init__()

    def find_packages(
        self,
        name,  # type: str
        constraint=None,  # type: Union[VersionConstraint, str, None]
        extras=None,  # type: Union[list, None]
        allow_prereleases=False,  # type: bool
    ):  # type: (...) -> List[Package]
        """
        Find packages on the remote server.
        """
        if constraint is None:
            constraint = "*"

        if not isinstance(constraint, VersionConstraint):
            constraint = parse_constraint(constraint)

        if isinstance(constraint, VersionRange):
            if (
                constraint.max is not None
                and constraint.max.is_prerelease()
                or constraint.min is not None
                and constraint.min.is_prerelease()
            ):
                allow_prereleases = True

        info = self.get_package_info(name)

        packages = []

        for version, release in info["releases"].items():
            if not release:
                # Bad release
                self._log(
                    "No release information found for {}-{}, skipping".format(
                        name, version
                    ),
                    level="debug",
                )
                continue

            try:
                package = Package(name, version)
            except ParseVersionError:
                self._log(
                    'Unable to parse version "{}" for the {} package, skipping'.format(
                        version, name
                    ),
                    level="debug",
                )
                continue

            if package.is_prerelease() and not allow_prereleases:
                continue

            if not constraint or (constraint and constraint.allows(package.version)):
                if extras is not None:
                    package.requires_extras = extras

                packages.append(package)

        self._log(
            "{} packages found for {} {}".format(len(packages), name, str(constraint)),
            level="debug",
        )

        return packages

    def package(
        self,
        name,  # type: str
        version,  # type: str
        extras=None,  # type: (Union[list, None])
    ):  # type: (...) -> Union[Package, None]
        if extras is None:
            extras = []

        release_info = self.get_release_info(name, version)
        package = Package(name, version, version)
        requires_dist = release_info["requires_dist"] or []
        for req in requires_dist:
            try:
                dependency = dependency_from_pep_508(req)
            except InvalidMarker:
                # Invalid marker
                # We strip the markers hoping for the best
                req = req.split(";")[0]

                dependency = dependency_from_pep_508(req)
            except ValueError:
                # Likely unable to parse constraint so we skip it
                self._log(
                    "Invalid constraint ({}) found in {}-{} dependencies, "
                    "skipping".format(req, package.name, package.version),
                    level="debug",
                )
                continue

            if dependency.in_extras:
                for extra in dependency.in_extras:
                    if extra not in package.extras:
                        package.extras[extra] = []

                    package.extras[extra].append(dependency)

            if not dependency.is_optional():
                package.requires.append(dependency)

        # Adding description
        package.description = release_info.get("summary", "")

        if release_info["requires_python"]:
            package.python_versions = release_info["requires_python"]

        if release_info["platform"]:
            package.platform = release_info["platform"]

        # Adding hashes information
        package.hashes = release_info["digests"]

        # Activate extra dependencies
        for extra in extras:
            if extra in package.extras:
                for dep in package.extras[extra]:
                    dep.activate()

                package.requires += package.extras[extra]

        return package

    def search(self, query, mode=0):
        results = []

        search = {"name": query}

        if mode == self.SEARCH_FULLTEXT:
            search["summary"] = query

        client = ServerProxy("https://pypi.python.org/pypi")
        hits = client.search(search, "or")

        for hit in hits:
            result = Package(hit["name"], hit["version"], hit["version"])
            result.description = to_str(hit["summary"])
            results.append(result)

        return results

    def get_package_info(self, name):  # type: (str) -> dict
        """
        Return the package information given its name.

        The information is returned from the cache if it exists
        or retrieved from the remote server.
        """
        if self._disable_cache:
            return self._get_package_info(name)

        return self._cache.store("packages").remember_forever(
            name, lambda: self._get_package_info(name)
        )

    def _get_package_info(self, name):  # type: (str) -> dict
        data = self._get("pypi/{}/json".format(name))
        if data is None:
            raise PackageNotFound("Package [{}] not found.".format(name))

        return data

    def get_release_info(self, name, version):  # type: (str, str) -> dict
        """
        Return the release information given a package name and a version.

        The information is returned from the cache if it exists
        or retrieved from the remote server.
        """
        if self._disable_cache:
            return self._get_release_info(name, version)

        cached = self._cache.remember_forever(
            "{}:{}".format(name, version), lambda: self._get_release_info(name, version)
        )

        cache_version = cached.get("_cache_version", "0.0.0")
        if parse_constraint(cache_version) != self.CACHE_VERSION:
            # The cache must be updated
            self._log(
                "The cache for {} {} is outdated. Refreshing.".format(name, version),
                level="debug",
            )
            cached = self._get_release_info(name, version)

            self._cache.forever("{}:{}".format(name, version), cached)

        return cached

    def _get_release_info(self, name, version):  # type: (str, str) -> dict
        self._log("Getting info for {} ({}) from PyPI".format(name, version), "debug")

        json_data = self._get("pypi/{}/{}/json".format(name, version))
        if json_data is None:
            raise PackageNotFound("Package [{}] not found.".format(name))

        info = json_data["info"]
        data = {
            "name": info["name"],
            "version": info["version"],
            "summary": info["summary"],
            "platform": info["platform"],
            "requires_dist": info["requires_dist"],
            "requires_python": info["requires_python"],
            "digests": [],
            "_cache_version": str(self.CACHE_VERSION),
        }

        try:
            version_info = json_data["releases"][version]
        except KeyError:
            version_info = []

        for file_info in version_info:
            data["digests"].append(file_info["digests"]["sha256"])

        if self._fallback and data["requires_dist"] is None:
            self._log("No dependencies found, downloading archives", level="debug")
            # No dependencies set (along with other information)
            # This might be due to actually no dependencies
            # or badly set metadata when uploading
            # So, we need to make sure there is actually no
            # dependencies by introspecting packages
            urls = defaultdict(list)
            for url in json_data["urls"]:
                # Only get sdist and wheels if they exist
                dist_type = url["packagetype"]
                if dist_type not in ["sdist", "bdist_wheel"]:
                    continue

                urls[dist_type].append(url["url"])

            if not urls:
                return data

            info = self._get_info_from_urls(urls)

            data["requires_dist"] = info["requires_dist"]

            if not data["requires_python"]:
                data["requires_python"] = info["requires_python"]

        return data

    def _get(self, endpoint):  # type: (str) -> Union[dict, None]
        json_response = self._session.get(self._url + endpoint)
        if json_response.status_code == 404:
            return None

        json_data = json_response.json()

        return json_data

    def _get_info_from_urls(
        self, urls
    ):  # type: (Dict[str, List[str]]) -> Dict[str, Union[str, List, None]]
        # Checking wheels first as they are more likely to hold
        # the necessary information
        if "bdist_wheel" in urls:
            # Check fo a universal wheel
            wheels = urls["bdist_wheel"]

            universal_wheel = None
            universal_python2_wheel = None
            universal_python3_wheel = None
            platform_specific_wheels = []
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
                    platform_specific_wheels.append(wheel)

            if universal_wheel is not None:
                return self._get_info_from_wheel(universal_wheel)

            info = {}
            if universal_python2_wheel and universal_python3_wheel:
                info = self._get_info_from_wheel(universal_python2_wheel)

                py3_info = self._get_info_from_wheel(universal_python3_wheel)
                if py3_info["requires_dist"]:
                    if not info["requires_dist"]:
                        info["requires_dist"] = py3_info["requires_dist"]

                        return info

                    py2_requires_dist = set(
                        dependency_from_pep_508(r).to_pep_508()
                        for r in info["requires_dist"]
                    )
                    py3_requires_dist = set(
                        dependency_from_pep_508(r).to_pep_508()
                        for r in py3_info["requires_dist"]
                    )
                    base_requires_dist = py2_requires_dist & py3_requires_dist
                    py2_only_requires_dist = py2_requires_dist - py3_requires_dist
                    py3_only_requires_dist = py3_requires_dist - py2_requires_dist

                    # Normalizing requires_dist
                    requires_dist = list(base_requires_dist)
                    for requirement in py2_only_requires_dist:
                        dep = dependency_from_pep_508(requirement)
                        dep.marker = dep.marker.intersect(
                            parse_marker("python_version == '2.7'")
                        )
                        requires_dist.append(dep.to_pep_508())

                    for requirement in py3_only_requires_dist:
                        dep = dependency_from_pep_508(requirement)
                        dep.marker = dep.marker.intersect(
                            parse_marker("python_version >= '3'")
                        )
                        requires_dist.append(dep.to_pep_508())

                    info["requires_dist"] = sorted(list(set(requires_dist)))

            if info:
                return info

            if platform_specific_wheels and "sdist" not in urls:
                # Pick the first wheel available and hope for the best
                return self._get_info_from_wheel(platform_specific_wheels[0])

        return self._get_info_from_sdist(urls["sdist"][0])

    def _get_info_from_wheel(
        self, url
    ):  # type: (str) -> Dict[str, Union[str, List, None]]
        self._log(
            "Downloading wheel: {}".format(urlparse.urlparse(url).path.rsplit("/")[-1]),
            level="debug",
        )
        info = {"summary": "", "requires_python": None, "requires_dist": None}

        filename = os.path.basename(urlparse.urlparse(url).path.rsplit("/")[-1])

        with temporary_directory() as temp_dir:
            filepath = os.path.join(temp_dir, filename)
            self._download(url, filepath)

            try:
                meta = pkginfo.Wheel(filepath)
            except ValueError:
                # Unable to determine dependencies
                # Assume none
                return info

        if meta.summary:
            info["summary"] = meta.summary or ""

        info["requires_python"] = meta.requires_python

        if meta.requires_dist:
            info["requires_dist"] = meta.requires_dist

        return info

    def _get_info_from_sdist(
        self, url
    ):  # type: (str) -> Dict[str, Union[str, List, None]]
        self._log(
            "Downloading sdist: {}".format(urlparse.urlparse(url).path.rsplit("/")[-1]),
            level="debug",
        )
        info = {"summary": "", "requires_python": None, "requires_dist": None}

        filename = os.path.basename(urlparse.urlparse(url).path)

        with temporary_directory() as temp_dir:
            filepath = Path(temp_dir) / filename
            self._download(url, str(filepath))

            try:
                meta = pkginfo.SDist(str(filepath))
                if meta.summary:
                    info["summary"] = meta.summary

                if meta.requires_python:
                    info["requires_python"] = meta.requires_python

                if meta.requires_dist:
                    info["requires_dist"] = list(meta.requires_dist)

                    return info
            except ValueError:
                # Unable to determine dependencies
                # We pass and go deeper
                pass

            # Still not dependencies found
            # So, we unpack and introspect
            suffix = filepath.suffix
            gz = None
            if suffix == ".zip":
                tar = zipfile.ZipFile(str(filepath))
            else:
                if suffix == ".bz2":
                    gz = BZ2File(str(filepath))
                    suffixes = filepath.suffixes
                    if len(suffixes) > 1 and suffixes[-2] == ".tar":
                        suffix = ".tar.bz2"
                else:
                    gz = GzipFile(str(filepath))
                    suffix = ".tar.gz"

                tar = tarfile.TarFile(str(filepath), fileobj=gz)

            try:
                tar.extractall(os.path.join(temp_dir, "unpacked"))
            finally:
                if gz:
                    gz.close()

                tar.close()

            unpacked = Path(temp_dir) / "unpacked"
            sdist_dir = unpacked / Path(filename).name.rstrip(suffix)

            # Checking for .egg-info at root
            eggs = list(sdist_dir.glob("*.egg-info"))
            if eggs:
                egg_info = eggs[0]

                requires = egg_info / "requires.txt"
                if requires.exists():
                    with requires.open() as f:
                        info["requires_dist"] = parse_requires(f.read())

                        return info

            # Searching for .egg-info in sub directories
            eggs = list(sdist_dir.glob("**/*.egg-info"))
            if eggs:
                egg_info = eggs[0]

                requires = egg_info / "requires.txt"
                if requires.exists():
                    with requires.open() as f:
                        info["requires_dist"] = parse_requires(f.read())

                        return info

            # Still nothing, try reading (without executing it)
            # the setup.py file.
            try:
                setup_info = self._inspect_sdist_with_setup(sdist_dir)

                for key, value in info.items():
                    if value:
                        continue

                    info[key] = setup_info[key]

                return info
            except Exception as e:
                self._log(
                    "An error occurred when reading setup.py or setup.cfg: {}".format(
                        str(e)
                    ),
                    "warning",
                )
                return info

    def _inspect_sdist_with_setup(self, sdist_dir):
        info = {"requires_python": None, "requires_dist": None}

        result = SetupReader.read_from_directory(sdist_dir)
        requires = ""
        for dep in result["install_requires"]:
            requires += dep + "\n"

        if result["extras_require"]:
            requires += "\n"

        for extra_name, deps in result["extras_require"].items():
            requires += "[{}]\n".format(extra_name)

            for dep in deps:
                requires += dep + "\n"

            requires += "\n"

        info["requires_dist"] = parse_requires(requires)
        info["requires_python"] = result["python_requires"]

        return info

    def _download(self, url, dest):  # type: (str, str) -> None
        r = get(url, stream=True)
        r.raise_for_status()

        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

    def _log(self, msg, level="info"):
        getattr(logger, level)("<comment>{}:</comment> {}".format(self._name, msg))
