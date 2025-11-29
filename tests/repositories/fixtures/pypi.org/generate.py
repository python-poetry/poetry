"""
This is a helper script built to generate mocked PyPI json files and release files. Executing the script does the
following for a specified list of releases.

1. Fetch relevant project json file from https://pypi.org/simple/<name>.
2. Fetch relevant release json file from https://pypi.org/pypi/<name>/<version>/json.
3. Download all files (if not otherwise specified) for each release, including <filename>.metadata files.
4. Stub (zero-out) all files not relevant for test cases, only sdist and bdist metadata is retained.
    a, We also retain `__init__.py` files as some packages use it for dynamic version detection when building sdist.
    b. Some release bdist, notably that of setuptools, wheel and poetry-core are retained as is in the `dist/` directory
        as these are required for some test cases.
    c. All stubbed files are written out to `stubbed/` directory.
    d. All stubbed files produce a consistent hash.
5. New checksums (sha256 and md5) are calculated and replaced in the following locations.
    a. All mocked json files.
    b. Installation lock file fixtures.
    c. Legacy Repository mocked html files.
6. All unwanted files and metadata is removed from any json file written. This includes any release versions removed.
7. A distribution hash getter fixture is generated.

The following also applies.

1. Local json files are preferred over remote ones unless `refresh=True` is specified.
    a. On removal or addition of a new version for a package, the base package must be refreshed. Otherwise,
       the new files added will not reflect in the file.
    b. You can also remove the existing file and re-run the script.
2. Download of distributions already present in `dist/` is skipped.
3. The `stubbed/` directory is cleared for each run.
"""

from __future__ import annotations

import dataclasses
import hashlib
import io
import json
import logging
import os
import re
import shutil
import sys
import tarfile
import zipfile

from functools import cached_property
from gzip import GzipFile
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from packaging.metadata import parse_email
from poetry.core.masonry.utils.helpers import normalize_file_permissions
from poetry.core.packages.package import Package

from poetry.repositories.pypi_repository import PyPiRepository
from tests.helpers import FIXTURE_PATH
from tests.helpers import FIXTURE_PATH_DISTRIBUTIONS
from tests.helpers import FIXTURE_PATH_INSTALLATION
from tests.helpers import FIXTURE_PATH_REPOSITORIES
from tests.helpers import FIXTURE_PATH_REPOSITORIES_LEGACY
from tests.helpers import FIXTURE_PATH_REPOSITORIES_PYPI


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterator

    import requests

    from poetry.core.packages.utils.link import Link

ENABLE_RELEASE_JSON = True

logger = logging.getLogger("pypi.generator")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
logger.addHandler(handler)


@dataclasses.dataclass(frozen=True)
class _ReleaseFileLocations:
    dist: Path = dataclasses.field(
        default=FIXTURE_PATH_REPOSITORIES_PYPI.joinpath("dist")
    )
    mocked: Path = dataclasses.field(
        default=FIXTURE_PATH_REPOSITORIES_PYPI.joinpath("dist", "mocked")
    )
    stubbed: Path = dataclasses.field(
        default=FIXTURE_PATH_REPOSITORIES_PYPI.joinpath("stubbed")
    )
    demo: Path = dataclasses.field(default=FIXTURE_PATH_DISTRIBUTIONS)


RELEASE_FILE_LOCATIONS = _ReleaseFileLocations()


@dataclasses.dataclass
class ReleaseFileMetadata:
    path: Path
    md5: str = dataclasses.field(init=False)
    sha256: str = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        data = self.path.read_bytes()
        self.sha256 = hashlib.sha256(data).hexdigest()
        self.md5 = hashlib.md5(data).hexdigest()


class _ReleaseFileCollection:
    def __init__(self, locations: list[Path] | None = None) -> None:
        self.locations = locations or [
            RELEASE_FILE_LOCATIONS.dist,
            RELEASE_FILE_LOCATIONS.stubbed,
        ]

    def filename_exists(self, filename: str) -> bool:
        return any(location.joinpath(filename).exists() for location in self.locations)

    def find(self, filename: str) -> ReleaseFileMetadata | None:
        for location in self.locations:
            if location.joinpath(filename).exists():
                return ReleaseFileMetadata(location)
        return None

    def list(self, location: Path | None = None) -> Iterator[ReleaseFileMetadata]:
        locations = [location] if location is not None else self.locations
        for candidate in locations:
            for file in candidate.glob("*.tar.*"):
                yield ReleaseFileMetadata(file)

            for file in candidate.glob("*.zip"):
                yield ReleaseFileMetadata(file)

            for file in candidate.glob("*.whl"):
                yield ReleaseFileMetadata(file)


RELEASE_FILE_COLLECTION = _ReleaseFileCollection()


def generate_distribution_hashes_fixture(files: list[ReleaseFileMetadata]) -> None:
    fixture_py = FIXTURE_PATH_REPOSITORIES / "distribution_hashes.py"
    files.sort(key=lambda f: f.path.name)

    text = ",\n".join(
        [
            f'    "{file.path.name}": DistributionHash(\n'
            f'        "{file.sha256}",\n'
            f'        "{file.md5}",\n'
            f"    )"
            for file in files
        ]
    )

    logger.info(
        "Generating fixture file at %s",
        fixture_py.relative_to(FIXTURE_PATH.parent.parent),
    )

    fixture_py.write_text(
        f"""# this file is generated by {Path(__file__).relative_to(FIXTURE_PATH.parent.parent).as_posix()}
from __future__ import annotations

import dataclasses

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from tests.types import DistributionHashGetter


@dataclasses.dataclass
class DistributionHash:
    sha256: str = ""
    md5: str = ""


KNOWN_DISTRIBUTION_HASHES = {{
{text},
}}


@pytest.fixture
def dist_hash_getter() -> DistributionHashGetter:
    def get_hash(name: str) -> DistributionHash:
        return KNOWN_DISTRIBUTION_HASHES.get(name, DistributionHash())

    return get_hash
""",
        encoding="utf-8",
    )


def cleanup_legacy_html_hashes(metadata: ReleaseFileMetadata) -> None:
    for index in FIXTURE_PATH_REPOSITORIES_LEGACY.glob("*.html"):
        existing_content = index.read_text(encoding="utf-8")

        content = re.sub(
            f"{metadata.path.name}#sha256=[A-Fa-f0-9]{{64}}",
            f"{metadata.path.name}#sha256={metadata.sha256}",
            existing_content,
        )
        content = re.sub(
            f'data-dist-info-metadata="sha256=[A-Fa-f0-9]{{64}}">{metadata.path.name}<',
            f'data-dist-info-metadata="sha256={metadata.sha256}">{metadata.path.name}<',
            content,
        )
        content = re.sub(
            f"{metadata.path.name}#md5=[A-Fa-f0-9]{{32}}",
            f"{metadata.path.name}#md5={metadata.md5}",
            content,
        )
        content = re.sub(
            f'data-dist-info-metadata="md5=[A-Fa-f0-9]{{32}}">{metadata.path.name}<',
            f'data-dist-info-metadata="md5={metadata.md5}">{metadata.path.name}<',
            content,
        )

        if existing_content != content:
            logger.info("Rewriting hashes in %s", index)
            index.write_text(content, encoding="utf-8")


def cleanup_installation_fixtures(metadata: ReleaseFileMetadata) -> None:
    for file in FIXTURE_PATH_INSTALLATION.glob("*.test"):
        original_content = file.read_text(encoding="utf-8")

        content = re.sub(
            f'file = "{metadata.path.name}", hash = "sha256:[A-Fa-f0-9]{{64}}"',
            f'file = "{metadata.path.name}", hash = "sha256:{metadata.sha256}"',
            original_content,
        )
        content = re.sub(
            f'file = "{metadata.path.name}", hash = "md5:[A-Fa-f0-9]{{32}}"',
            f'file = "{metadata.path.name}", hash = "md5:{metadata.md5}"',
            content,
        )

        if content != original_content:
            logger.info("Rewriting hashes in %s", file)
            file.write_text(content, encoding="utf-8")


class FileManager:
    def __init__(self, pypi: PyPiRepository) -> None:
        self.pypi = pypi

    @staticmethod
    def should_preserve_file_content_check(link: Link) -> Callable[[str], bool]:
        def sdist_check(filename: str) -> bool:
            return filename in {
                "pyproject.toml",
                "setup.py",
                "setup.cfg",
                "PKG-INFO",
                "__init__.py",
                "requires.txt",
                "requirements.txt",
                "entry_points.txt",
                "top_level.txt",
            }

        bdist_preserve_regex = re.compile(r"^((?!/).)*\.dist-info/((?!/).)*$")

        def bdist_check(filename: str) -> bool:
            return bool(bdist_preserve_regex.match(filename))

        if link.is_sdist:
            return sdist_check

        return bdist_check

    def process_metadata_file(self, link: Link) -> None:
        # we enforce the availability of the metadata file
        link._metadata = True

        logger.info("Processing metadata file for %s", link.filename)

        assert link.metadata_url is not None
        response: requests.Response = self.pypi.session.get(
            link.metadata_url, raise_for_status=False
        )

        if response.status_code != 200:
            logger.info("Skipping metadata for %s", link.filename)
            return None

        metadata, _ = parse_email(response.content)
        content = response.content.decode(encoding="utf-8").replace(
            metadata["description"], ""
        )

        FIXTURE_PATH_REPOSITORIES_PYPI.joinpath(
            "metadata", f"{link.filename}.metadata"
        ).write_text(content, encoding="utf-8", newline="\n")

    def copy_as_is(self, link: Link) -> ReleaseFileMetadata:
        dst = FIXTURE_PATH_REPOSITORIES_PYPI / "dists" / link.filename
        logger.info(
            "Preserving release file from %s to %s",
            link.url,
            dst.relative_to(FIXTURE_PATH_REPOSITORIES_PYPI),
        )

        with self.pypi._cached_or_downloaded_file(link) as src:
            shutil.copy(src, dst)

        return ReleaseFileMetadata(dst)

    def process_zipfile(self, link: Link) -> ReleaseFileMetadata:
        dst = FIXTURE_PATH_REPOSITORIES_PYPI / "stubbed" / link.filename
        is_protected = self.should_preserve_file_content_check(link)

        logger.info(
            "Stubbing release file from %s to %s",
            link.url,
            dst.relative_to(FIXTURE_PATH_REPOSITORIES_PYPI),
        )

        with (
            self.pypi._cached_or_downloaded_file(link) as src,
            zipfile.ZipFile(
                dst, "w", compression=zipfile.ZIP_DEFLATED
            ) as stubbed_sdist,
            zipfile.ZipFile(src) as zf,
        ):
            for member in zf.infolist():
                if not is_protected(member.filename):
                    logger.debug("Stubbing file %s(%s)", link.filename, member.filename)
                    stubbed_sdist.writestr(member, io.BytesIO().getvalue())

                elif Path(member.filename).name == "RECORD":
                    # Since unprotected files are stubbed to be zero size, the RECORD file must
                    # be updated to match.
                    stubbed_content = io.StringIO()
                    for line in zf.read(member.filename).decode("utf-8").splitlines():
                        filename = line.split(",")[0]
                        if is_protected(filename):
                            stubbed_content.write(f"{line}\n")
                            continue

                        stubbed_line = re.sub(
                            ",sha256=.*",
                            ",sha256=47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU,0",
                            line,
                        )
                        stubbed_content.write(f"{stubbed_line}\n")

                    stubbed_sdist.writestr(member, stubbed_content.getvalue())

                else:
                    logger.debug(
                        "Preserving file %s(%s)", link.filename, member.filename
                    )
                    stubbed_sdist.writestr(member, zf.read(member.filename))

        return ReleaseFileMetadata(dst)

    def process_tarfile(self, link: Link) -> ReleaseFileMetadata:
        dst = FIXTURE_PATH_REPOSITORIES_PYPI / "stubbed" / link.filename
        is_protected = self.should_preserve_file_content_check(link)

        logger.info(
            "Stubbing release file from %s to %s",
            link.url,
            dst.relative_to(FIXTURE_PATH_REPOSITORIES_PYPI),
        )

        with (
            self.pypi._cached_or_downloaded_file(link) as src,
            GzipFile(dst.as_posix(), mode="wb", mtime=0) as gz,
            tarfile.TarFile(
                dst, mode="w", fileobj=gz, format=tarfile.PAX_FORMAT
            ) as dst_tf,
            tarfile.open(src, "r") as src_tf,
        ):
            for member in src_tf.getmembers():
                member.uid = 0
                member.gid = 0
                member.uname = ""
                member.gname = ""
                member.mtime = 0
                member.mode = normalize_file_permissions(member.mode)

                if member.isfile() and not is_protected(Path(member.name).name):
                    logger.debug("Stubbing file %s(%s)", link.filename, member.name)
                    file_obj = io.BytesIO()
                    member.size = file_obj.getbuffer().nbytes
                    dst_tf.addfile(member, file_obj)
                else:
                    logger.debug("Preserving file %s(%s)", link.filename, member.name)
                    dst_tf.addfile(member, src_tf.extractfile(member))

        os.utime(dst, (0, 0))

        return ReleaseFileMetadata(dst)


class Project:
    def __init__(self, name: str, releases: list[Release]):
        self.name = name
        self.releases: list[Release] = releases

    @property
    def filenames(self) -> list[str]:
        filenames = []

        for release in self.releases:
            filenames.extend(release.filenames)

        return filenames

    @property
    def files(self) -> list[ReleaseFileMetadata]:
        files = []

        for release in self.releases:
            files.extend(release.files)

        return files

    @property
    def versions(self) -> list[str]:
        return [release.version for release in self.releases]

    @cached_property
    def json_path(self) -> Path:
        return FIXTURE_PATH_REPOSITORIES_PYPI.joinpath("json", f"{self.name}.json")

    @staticmethod
    def _finalise_file_item(
        data: dict[str, Any], files: list[ReleaseFileMetadata] | None = None
    ) -> dict[str, Any]:
        filename = data["filename"]

        for file in files or []:
            if file.path.name == filename:
                data["hashes"] = {"md5": file.md5, "sha256": file.sha256}
                break

        metadata_file = (
            FIXTURE_PATH_REPOSITORIES_PYPI / "metadata" / f"{filename}.metadata"
        )

        if metadata_file.exists():
            metadata = ReleaseFileMetadata(metadata_file)
            for key in ["core-metadata", "data-dist-info-metadata"]:
                data[key] = {"sha256": metadata.sha256}

        return data

    def _finalise(self, data: dict[str, Any]) -> None:
        files = self.files

        data["versions"] = self.versions

        data["files"] = [
            self._finalise_file_item(_file, files)
            for _file in data["files"]
            if _file["filename"] in self.filenames
        ]

        data["meta"]["_last-serial"] = 0

        logger.info(
            "Finalising up %s",
            self.json_path.relative_to(FIXTURE_PATH_REPOSITORIES_PYPI),
        )
        self.json_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        for file in files:
            cleanup_installation_fixtures(file)
            cleanup_legacy_html_hashes(file)

    def populate(self, pypi: PyPiRepository) -> None:
        logger.info("Fetching remote json via https://pypi.org/simple/%s", self.name)
        data = (
            pypi._get(
                f"simple/{self.name}/",
                headers={"Accept": "application/vnd.pypi.simple.v1+json"},
            )
            or {}
        )

        for release in self.releases:
            release.populate(pypi)

        self._finalise(data)


class Release:
    def __init__(
        self,
        name: str,
        version: str,
        download_files: bool = True,
        stub: bool = True,
        preserved_files: list[str] | None = None,
    ):
        self.name = name
        self.version = version
        self.filenames: list[str] = preserved_files or []
        self.download_files: bool = download_files
        self.stub: bool = stub
        self.files: list[ReleaseFileMetadata] = []

    @cached_property
    def json_path(self) -> Path:
        return (
            FIXTURE_PATH_REPOSITORIES_PYPI / "json" / self.name / f"{self.version}.json"
        )

    @staticmethod
    def _finalise_file_item(
        data: dict[str, Any], files: list[ReleaseFileMetadata] | None = None
    ) -> dict[str, Any]:
        filename = data["filename"]

        for file in files or []:
            if file.path.name == filename:
                data["digests"] = {"md5": file.md5, "sha256": file.sha256}
                data["md5_digest"] = file.md5
                break

        return data

    def _finalise(self, data: dict[str, Any]) -> None:
        data.get("info", {"description": ""})["description"] = ""

        if "vulnerabilities" in data:
            data["vulnerabilities"] = []

        data["urls"] = [
            self._finalise_file_item(item, self.files)
            for item in data["urls"]
            if item["filename"] in self.filenames
        ]

        for item in data["urls"]:
            self._finalise_file_item(item, self.files)

        data["last_serial"] = 0

        logger.info(
            "Finalising up %s",
            self.json_path.relative_to(FIXTURE_PATH_REPOSITORIES_PYPI),
        )

        if not self.json_path.parent.exists():
            self.json_path.parent.mkdir(parents=True, exist_ok=True)

        self.json_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def populate(self, pypi: PyPiRepository) -> None:
        fm = FileManager(pypi)

        links = pypi.find_links_for_package(Package(self.name, self.version))

        for link in links:
            self.filenames.append(link.filename)

            fm.process_metadata_file(link)

            if self.download_files:
                if not self.stub and link.is_wheel:
                    file = fm.copy_as_is(link)
                elif link.is_wheel or (
                    link.is_sdist and link.filename.endswith(".zip")
                ):
                    file = fm.process_zipfile(link)
                else:
                    file = fm.process_tarfile(link)

                self.files.append(file)

        if ENABLE_RELEASE_JSON:
            logger.info(
                "Fetching remote json via https://pypi.org/pypi/%s/%s/json",
                self.name,
                self.version,
            )
            data = pypi._get(f"pypi/{self.name}/{self.version}/json") or {}
            self._finalise(data)


def cleanup_old_files(releases: dict[str, list[str]]) -> None:
    json_fixture_path = FIXTURE_PATH_REPOSITORIES_PYPI / "json"

    for json_file in json_fixture_path.glob("*.json"):
        if json_file.stem not in releases and json_file.stem not in {"isort-metadata"}:
            json_file.unlink()

    for json_file in json_fixture_path.glob("*/*.json"):
        if json_file.parent.name == "mocked":
            continue

        if (
            json_file.parent.name not in releases
            or json_file.stem not in releases[json_file.parent.name]
        ):
            logger.info(
                "Removing unmanaged release file %s",
                json_file.relative_to(FIXTURE_PATH_REPOSITORIES_PYPI),
            )
            json_file.unlink()

            if len(list(json_file.parent.iterdir())) == 0:
                logger.info(
                    "Removing empty directory %s",
                    json_file.parent.relative_to(FIXTURE_PATH_REPOSITORIES_PYPI),
                )
                json_file.parent.rmdir()


PROJECTS = [
    Project("attrs", releases=[Release("attrs", "17.4.0")]),
    Project(
        "black", releases=[Release("black", "19.10b0"), Release("black", "21.11b0")]
    ),
    Project("cleo", releases=[Release("cleo", "1.0.0a5")]),
    Project("clikit", releases=[Release("clikit", "0.2.4")]),
    # tests.installation.test_installer.test_installer_with_pypi_repository on windows
    Project("colorama", releases=[Release("colorama", "0.3.9")]),
    Project("discord-py", releases=[Release("discord-py", "2.0.0")]),
    Project("funcsigs", releases=[Release("funcsigs", "1.0.2", download_files=False)]),
    Project("filecache", releases=[Release("filecache", "0.81", download_files=False)]),
    Project("futures", releases=[Release("futures", "3.2.0")]),
    # tests.repositories.test_pypi_repository.test_get_release_info_includes_only_supported_types
    Project(
        "hbmqtt",
        releases=[
            Release(
                "hbmqtt",
                "0.9.6",
                preserved_files=[
                    "hbmqtt-0.9.6.linux-x86_64.tar.gz",
                    "hbmqtt-0.9.6-py3.8.egg",
                ],
            )
        ],
    ),
    Project(
        "importlib-metadata",
        releases=[Release("importlib-metadata", "1.7.0", download_files=False)],
    ),
    Project(
        "ipython",
        releases=[
            Release("ipython", "4.1.0rc1", download_files=False),
            # tests.repositories.test_legacy_repository.test_get_package_from_both_py2_and_py3_specific_wheels
            # tests.repositories.test_legacy_repository.test_get_package_retrieves_non_sha256_hashes_mismatching_known_hash
            Release("ipython", "5.7.0"),
            # tests.repositories.test_legacy_repository.test_get_package_retrieves_non_sha256_hashes
            # tests.repositories.test_legacy_repository.test_get_package_with_dist_and_universal_py3_wheel
            Release("ipython", "7.5.0"),
        ],
    ),
    # yanked, no dependencies
    Project("isodate", releases=[Release("isodate", "0.7.0")]),
    Project("isort", releases=[Release("isort", "4.3.4")]),
    Project("jupyter", releases=[Release("jupyter", "1.0.0")]),
    Project("more-itertools", releases=[Release("more-itertools", "4.1.0")]),
    Project("pastel", releases=[Release("pastel", "0.1.0")]),
    Project("pluggy", releases=[Release("pluggy", "0.6.0")]),
    Project(
        "poetry-core",
        releases=[
            Release("poetry-core", "1.5.0", stub=False),
            Release("poetry-core", "2.0.1", stub=False),
        ],
    ),
    Project("py", releases=[Release("py", "1.5.3")]),
    Project("pylev", releases=[Release("pylev", "1.3.0", download_files=False)]),
    Project(
        "pytest", releases=[Release("pytest", "3.5.0"), Release("pytest", "3.5.1")]
    ),
    # tests.repositories.test_legacy_repository.test_get_package_information_skips_dependencies_with_invalid_constraints
    Project(
        "python-language-server", releases=[Release("python-language-server", "0.21.2")]
    ),
    Project("pyyaml", releases=[Release("pyyaml", "3.13.0", download_files=False)]),
    # tests.repositories.test_pypi_repository.test_find_packages
    Project(
        "requests",
        releases=[
            Release("requests", "2.18.0", download_files=False),
            Release("requests", "2.18.1", download_files=False),
            Release("requests", "2.18.2", download_files=False),
            Release("requests", "2.18.3", download_files=False),
            # tests.repositories.test_pypi_repository.test_package
            Release("requests", "2.18.4", download_files=True),
            Release("requests", "2.19.0", download_files=False),
        ],
    ),
    Project(
        "setuptools",
        releases=[
            Release("setuptools", "39.2.0", download_files=False),
            Release("setuptools", "67.6.1", stub=False),
        ],
    ),
    Project("six", releases=[Release("six", "1.11.0")]),
    Project("sqlalchemy", releases=[Release("sqlalchemy", "1.2.12")]),
    # tests.repositories.test_pypi_repository.test_find_packages_with_prereleases
    Project(
        "toga",
        releases=[
            Release("toga", "0.3.0", download_files=False),
            Release("toga", "0.3.0dev1", download_files=False),
            Release("toga", "0.3.0dev2", download_files=False),
            Release("toga", "0.4.0", download_files=False),
        ],
    ),
    Project(
        "tomlkit", releases=[Release("tomlkit", "0.5.2"), Release("tomlkit", "0.5.3")]
    ),
    Project("twisted", releases=[Release("twisted", "18.9.0")]),
    Project("wheel", releases=[Release("wheel", "0.40.0", stub=False)]),
    Project("zipp", releases=[Release("zipp", "3.5.0")]),
]


def main() -> None:
    pypi = PyPiRepository(disable_cache=False)
    files: list[ReleaseFileMetadata] = []
    releases: dict[str, list[str]] = {}

    for project in PROJECTS:
        project = Project(project.name, releases=project.releases)
        project.populate(pypi)

        releases[project.name] = project.versions
        files.extend(project.files)

    rfc = _ReleaseFileCollection(
        [RELEASE_FILE_LOCATIONS.demo, RELEASE_FILE_LOCATIONS.mocked]
    )
    files.extend(rfc.list())

    generate_distribution_hashes_fixture(files)

    cleanup_old_files(releases)


if __name__ == "__main__":
    main()
