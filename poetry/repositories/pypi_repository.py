import email
import logging
import os
import pathlib
import struct
import urllib.parse
import zipfile
import zlib

from collections import defaultdict
from typing import Dict
from typing import List
from typing import Tuple
from typing import Union

from cachecontrol import CacheControl
from cachecontrol.caches.file_cache import FileCache
from cachecontrol.controller import logger as cache_control_logger
from cachy import CacheManager
from html5lib.html5parser import parse
from requests import get
from requests import session
from requests.exceptions import TooManyRedirects

from poetry.locations import CACHE_DIR
from poetry.packages import Package
from poetry.packages import dependency_from_pep_508
from poetry.packages.utils.link import Link
from poetry.semver import VersionConstraint
from poetry.semver import VersionRange
from poetry.semver import parse_constraint
from poetry.semver.exceptions import ParseVersionError
from poetry.utils._compat import Path
from poetry.utils._compat import to_str
from poetry.utils.helpers import temporary_directory
from poetry.utils.inspector import Inspector
from poetry.utils.patterns import wheel_file_re
from poetry.version.markers import InvalidMarker
from poetry.version.markers import parse_marker

from .exceptions import PackageNotFound
from .exceptions import WrongFile
from .repository import Repository


try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse


cache_control_logger.setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

RangeDescriptor = Union[Tuple[int], int]
MetadataDict = Dict[str, Union[str, List, None]]


class PyPiRepository(Repository):

    CACHE_VERSION = parse_constraint("1.0.0")

    def __init__(self, url="https://pypi.org/", disable_cache=False, fallback=True):
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

        self._cache_control_cache = FileCache(str(release_cache_dir / "_http"))
        self._session = CacheControl(session(), cache=self._cache_control_cache)
        self._inspector = Inspector()

        super(PyPiRepository, self).__init__()

        self._name = "PyPI"

    @property
    def url(self):  # type: () -> str
        return self._url

    @property
    def authenticated_url(self):  # type: () -> str
        return self._url

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

        try:
            info = self.get_package_info(name)
        except PackageNotFound:
            self._log(
                "No packages found for {} {}".format(name, str(constraint)),
                level="debug",
            )
            return []

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
        package.files = release_info["files"]

        # Activate extra dependencies
        for extra in extras:
            if extra in package.extras:
                for dep in package.extras[extra]:
                    dep.activate()

                package.requires += package.extras[extra]

        return package

    def search(self, query):
        results = []

        search = {"q": query}

        response = session().get(self._url + "search", params=search)
        content = parse(response.content, namespaceHTMLElements=False)
        for result in content.findall(".//*[@class='package-snippet']"):
            name = result.find("h3/*[@class='package-snippet__name']").text
            version = result.find("h3/*[@class='package-snippet__version']").text

            if not name or not version:
                continue

            description = result.find("p[@class='package-snippet__description']").text
            if not description:
                description = ""

            try:
                result = Package(name, version, description)
                result.description = to_str(description.strip())
                results.append(result)
            except ParseVersionError:
                self._log(
                    'Unable to parse version "{}" for the {} package, skipping'.format(
                        version, name
                    ),
                    level="debug",
                )

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
            "files": [],
            "_cache_version": str(self.CACHE_VERSION),
        }

        try:
            version_info = json_data["releases"][version]
        except KeyError:
            version_info = []

        for file_info in version_info:
            data["files"].append(
                {
                    "file": file_info["filename"],
                    "hash": "sha256:" + file_info["digests"]["sha256"],
                }
            )

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
        try:
            json_response = self._session.get(self._url + endpoint)
        except TooManyRedirects:
            # Cache control redirect loop.
            # We try to remove the cache and try again
            self._cache_control_cache.delete(self._url + endpoint)
            json_response = self._session.get(self._url + endpoint)

        if json_response.status_code == 404:
            return None

        json_data = json_response.json()

        return json_data

    def _get_info_from_urls(self, urls):  # type: (Dict[str, List[str]]) -> MetadataDict
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

            # Prefer non platform specific wheels
            if universal_python3_wheel:
                return self._get_info_from_wheel(universal_python3_wheel)

            if universal_python2_wheel:
                return self._get_info_from_wheel(universal_python2_wheel)

            if platform_specific_wheels and "sdist" not in urls:
                # Pick the first wheel available and hope for the best
                return self._get_info_from_wheel(platform_specific_wheels[0])

        return self._get_info_from_sdist(urls["sdist"][0])

    def _get_info_from_wheel(self, url):  # type: (str) -> MetadataDict
        self._log(
            "Downloading wheel: {}".format(urlparse.urlparse(url).path.rsplit("/")[-1]),
            level="debug",
        )

        filename = os.path.basename(urlparse.urlparse(url).path.rsplit("/")[-1])

        try:
            metadata = self._cherry_pick_metadata(url)
        except Exception as exc:
            self._log(
                "Wheel metadata cherry picking failed for url {url}: {exc}".format(
                    url=url, exc=exc
                ),
                level="debug",
            )
        else:
            self._log(
                "Successfully cherry picked metadata for url {}".format(url),
                level="debug",
            )
            return metadata

        with temporary_directory() as temp_dir:
            filepath = Path(temp_dir) / filename
            self._download(url, str(filepath))

            return self._inspector.inspect_wheel(filepath)

    def _get_info_from_sdist(self, url):  # type: (str) -> MetadataDict
        self._log(
            "Downloading sdist: {}".format(urlparse.urlparse(url).path.rsplit("/")[-1]),
            level="debug",
        )

        filename = os.path.basename(urlparse.urlparse(url).path)

        with temporary_directory() as temp_dir:
            filepath = Path(temp_dir) / filename
            self._download(url, str(filepath))

            return self._inspector.inspect_sdist(filepath)

    def _cherry_pick_metadata(self, url):  # type: (str) -> MetadataDict
        """
        This function downloads close to the minimum amount of bytes in order to
        extract the metadata from a wheel file accessed through an HTTP server
        supporting Range requests.
        """
        # How it works: A Wheel file is a zip file. The internal structure of a zip file
        # is as follows:
        # - For each file, there's a file header followed by the compressed file data
        # - Then after all files, there's a central directory saying where each file is
        #   inside the archive
        # - Then there's a final structure saying where the central directory begins.
        #
        # Because most wheel files are identical, we know that the METADATA file we're
        # looking for is the 5th to the end, and the position of the central directory
        # record related to this file starts "a little more" than 355 bytes from the
        # end. Here, "a little more" stands from the fact the path of the 5 last files
        # appear in the data, and while the filename are known, the folder name is
        # dynamic: it's `{package name}-{version}.dist-info`. As long as we know how
        # details on the package name and version, we can derive the exact offset of the
        # METADATA central directory record, and read it, extract the offset and size of
        # the file itself, then read the relevant part of the zip, extract the raw
        # compressed bytes of the METADATA file, decompress them and finally parse them.

        # Metadata file is named "{dist_name}.dist-info/METADATA" We'll both be looking
        # for that name, and counting the length of that name We probably already know
        # the information, but it might be tedious to pass the info all the way down, so
        # we can make it easier for us and extract it from the url
        dist_name = self._get_dist_name_from_url(url=url)
        path_format = "{dist_name}.dist-info/{filename}"
        metadata_filename = "METADATA"
        metadata_file_path = path_format.format(
            dist_name=dist_name, filename=metadata_filename
        )

        file_order = (
            metadata_filename,
            "WHEEL",
            "entry_points.txt",
            "top_level.txt",
            "RECORD",
        )

        size_central_dir = zipfile.sizeCentralDir
        size_end_central_dir = zipfile.sizeEndCentDir

        download_offset = size_end_central_dir + sum(
            size_central_dir
            + len(path_format.format(dist_name=dist_name, filename=filename))
            for filename in file_order
        )

        last_bytes = self._download_range(url=url, byte_range=-download_offset)

        # Checking all files from 5th
        for record_offset in self._search_records(zip_bytes=last_bytes):

            try:
                # Deriving the exact position and size of the METADATA record in the zip
                offset, size = self._get_metadata_record_location(
                    zip_bytes=last_bytes[record_offset:],
                    expected_filename=metadata_file_path,
                )
                break
            except WrongFile:
                continue
        else:
            raise ValueError("Could not find METADATA in the zip")

        # Now downloading the METADATA file header and the compressed bytes
        metadata_record_bytes = self._download_range(url=url, byte_range=(offset, size))

        # Checking and extracting the file
        metadata_bytes = self._extract_zipped_metadata(
            zip_bytes=metadata_record_bytes, expected_filename=metadata_file_path
        )

        # Finally, parse it
        return self._inspector.inspect_metadata_file(metadata_bytes=metadata_bytes)

    def _search_records(
        self, zip_bytes, separator=zipfile.stringCentralDir
    ):  # type (bytes) -> Iterable[int]
        offset = -1

        while True:
            offset = zip_bytes.find(separator, offset + 1)
            if offset == -1:
                return
            yield offset

    def _get_dist_name_from_url(self, url):  # type: (str) -> str
        components = urllib.parse.urlparse(url)
        filename = pathlib.Path(components.path).name
        package_name, version, _ = filename.split("-", 2)
        return "{}-{}".format(package_name, version)

    def _make_range_string(self, byte_range):  # type: (RangeDescriptor) -> str
        if isinstance(byte_range, tuple):
            begin, length = byte_range
            # HTTP ranges are inclusive on both sides, thus -1
            range = "{}-{}".format(begin, begin + length - 1)
        elif isinstance(byte_range, int) and byte_range < 0:
            range = str(byte_range)
        else:
            raise NotImplementedError()

        return "bytes={}".format(range)

    def _download_range(self, url, byte_range):  # type: (str, RangeDescriptor) -> bytes
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Range_requests
        r = get(url, headers={"Range": self._make_range_string(byte_range=byte_range)})
        r.raise_for_status()
        return r.content

    def _get_metadata_record_location(self, zip_bytes, expected_filename):
        size_central_dir = zipfile.sizeCentralDir
        size_file_header = zipfile.sizeFileHeader
        string_central_dir = zipfile.stringCentralDir
        struct_central_dir = zipfile.structCentralDir

        bytes_record = zip_bytes[:size_central_dir]
        record = struct.unpack(struct_central_dir, bytes_record)

        signature = record[zipfile._CD_SIGNATURE]
        compress_type = record[zipfile._CD_COMPRESS_TYPE]
        filename_length = record[zipfile._CD_FILENAME_LENGTH]
        compresses_size = record[zipfile._CD_COMPRESSED_SIZE]
        local_header_offset = record[zipfile._CD_LOCAL_HEADER_OFFSET]

        if signature != string_central_dir:
            raise ValueError("Bad magic number for central dir record")

        if compress_type != zipfile.ZIP_DEFLATED:
            raise ValueError("Non-standard wheel")

        filename = zip_bytes[
            size_central_dir : size_central_dir + filename_length
        ].decode("utf_8")

        if filename != expected_filename:
            raise WrongFile("File is {}, not {}".format(filename, expected_filename))

        # From the zip file format, we know we have the header (30 bytes), the filename,
        # the extra data (expected to be 0 bytes, we'll check later) and the compressed
        # file itself
        record_size = size_file_header + len(filename) + compresses_size

        return local_header_offset, record_size

    def _extract_zipped_metadata(self, zip_bytes, expected_filename):
        size_file_header = zipfile.sizeFileHeader
        string_file_header = zipfile.stringFileHeader
        struct_file_header = zipfile.structFileHeader

        bytes_header = zip_bytes[:size_file_header]
        header = struct.unpack(struct_file_header, bytes_header)

        signature = header[zipfile._FH_SIGNATURE]
        size_filename = header[zipfile._FH_FILENAME_LENGTH]
        size_data = header[zipfile._FH_COMPRESSED_SIZE]
        extra_length = header[zipfile._FH_EXTRA_FIELD_LENGTH]

        if signature != string_file_header:
            raise ValueError("Bad magic number for file header")

        if extra_length != 0:
            raise ValueError("Metadata header contains unexpected extra data")

        start_filename = size_file_header
        end_filename = start_filename + size_filename
        filename = zip_bytes[start_filename:end_filename].decode("utf_8")
        if filename != expected_filename:
            raise ValueError("File is {}, not {}".format(filename, expected_filename))

        if len(zip_bytes) != size_file_header + size_filename + size_data:
            raise ValueError("Problem computing data length")

        start_bytes = end_filename
        end_bytes = start_bytes + size_data

        file_bytes = zip_bytes[start_bytes:end_bytes]

        # We've checked that the compression uses zlib, so we use that directly
        # The -15 is pure magic, stolen from:
        # https://github.com/python/cpython/blob/6c7bb38ff2799ac218e6df598b2b262f89e2bc1e/Lib/zipfile.py#L683
        data = zlib.decompress(file_bytes, wbits=-15)

        return data

    def _download(self, url, dest):  # type: (str, str) -> None
        r = get(url, stream=True)
        r.raise_for_status()

        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

    def _log(self, msg, level="info"):
        getattr(logger, level)("<comment>{}:</comment> {}".format(self._name, msg))
