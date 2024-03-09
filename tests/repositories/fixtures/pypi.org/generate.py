"""
This is a helper script built to generate mocked PyPI json files and release files. Executing the script does the
following for a specified list of releases.

1. Fetch relevant project json file from https://pypi.org/simple/<name>.
2. Fetch relevant release json file from https://pypi.org/pypi/<name>/<version>/json.
3. Download all files (if not otherwise specified) for each release.
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

from abc import abstractmethod
from functools import cached_property
from gzip import GzipFile
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from typing import Iterator

from poetry.core.masonry.builders.sdist import SdistBuilder
from poetry.core.packages.package import Package
from tests.helpers import FIXTURE_PATH
from tests.helpers import FIXTURE_PATH_DISTRIBUTIONS
from tests.helpers import FIXTURE_PATH_INSTALLATION
from tests.helpers import FIXTURE_PATH_REPOSITORIES
from tests.helpers import FIXTURE_PATH_REPOSITORIES_LEGACY
from tests.helpers import FIXTURE_PATH_REPOSITORIES_PYPI

from poetry.repositories.pypi_repository import PyPiRepository


if TYPE_CHECKING:
    from poetry.core.packages.utils.link import Link

logger = logging.getLogger("pypi.generator")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
logger.addHandler(handler)


@dataclasses.dataclass
class ReleaseSpecification:
    name: str
    version: str
    stub: bool = True
    is_fake: bool = False

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ReleaseSpecification):
            return self.name == other.name and self.version == other.version
        return False


@dataclasses.dataclass
class ProjectSpecification:
    name: str
    ignore_missing_files: bool = False

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ProjectSpecification):
            return self.name == other.name
        return False


PROJECT_SPECS = [
    ProjectSpecification("requests", ignore_missing_files=True),
]

RELEASE_SPECS = [
    ReleaseSpecification("attrs", "17.4.0"),
    ReleaseSpecification("black", "19.10b0"),
    ReleaseSpecification("black", "21.11b0"),
    ReleaseSpecification("cachecontrol", "0.12.5", is_fake=True),
    ReleaseSpecification("cleo", "1.0.0a5"),
    ReleaseSpecification("clikit", "0.2.4"),
    # tests.installation.test_installer.test_installer_with_pypi_repository on windows
    ReleaseSpecification("colorama", "0.3.9"),
    ReleaseSpecification("discord-py", "2.0.0"),
    ReleaseSpecification("funcsigs", "1.0.2", is_fake=True),
    ReleaseSpecification("futures", "3.2.0"),
    ReleaseSpecification("hbmqtt", "0.9.6", is_fake=True),
    ReleaseSpecification("importlib-metadata", "1.7.0", is_fake=True),
    ReleaseSpecification("ipython", "4.1.0rc1", is_fake=True),
    # tests.repositories.test_legacy_repository.test_get_package_from_both_py2_and_py3_specific_wheels
    # tests.repositories.test_legacy_repository.test_get_package_retrieves_non_sha256_hashes_mismatching_known_hash
    ReleaseSpecification("ipython", "5.7.0"),
    # tests.repositories.test_legacy_repository.test_get_package_retrieves_non_sha256_hashes
    # tests.repositories.test_legacy_repository.test_get_package_with_dist_and_universal_py3_wheel
    ReleaseSpecification("ipython", "7.5.0"),
    ReleaseSpecification("isort", "4.3.4"),
    ReleaseSpecification("isort-metadata", "4.3.4", is_fake=True),
    ReleaseSpecification("jupyter", "1.0.0"),
    ReleaseSpecification("lockfile", "0.12.2", is_fake=True),
    ReleaseSpecification("more-itertools", "4.1.0"),
    ReleaseSpecification("pastel", "0.1.0"),
    ReleaseSpecification("pluggy", "0.6.0"),
    ReleaseSpecification("poetry", "0.12.4", is_fake=True),
    ReleaseSpecification("poetry-core", "1.5.0", stub=False),
    ReleaseSpecification("py", "1.5.3"),
    ReleaseSpecification("pygame-music-grid", "3.13", is_fake=True),
    ReleaseSpecification("pylev", "1.3.0", is_fake=True),
    ReleaseSpecification("pytest", "3.5.0"),
    ReleaseSpecification("pytest", "3.5.1"),
    # tests.repositories.test_legacy_repository.test_get_package_information_skips_dependencies_with_invalid_constraints
    ReleaseSpecification("python-language-server", "0.21.2"),
    ReleaseSpecification("pyyaml", "3.13.0", is_fake=True),
    ReleaseSpecification("requests", "2.18.4"),
    ReleaseSpecification("setuptools", "39.2.0", is_fake=True),
    ReleaseSpecification("setuptools", "67.6.1", stub=False),
    ReleaseSpecification("six", "1.11.0"),
    ReleaseSpecification("sqlalchemy", "1.2.12"),
    ReleaseSpecification("toga", "0.3.0", is_fake=True),
    ReleaseSpecification("tomlkit", "0.5.2"),
    ReleaseSpecification("tomlkit", "0.5.3"),
    ReleaseSpecification("trackpy", "0.4.1", is_fake=True),
    ReleaseSpecification("twisted", "18.9.0"),
    ReleaseSpecification("wheel", "0.40.0", stub=False),
    ReleaseSpecification("zipp", "3.5.0"),
]


@dataclasses.dataclass(frozen=True)
class _ReleaseFileLocations:
    dist: Path = dataclasses.field(
        default=FIXTURE_PATH_REPOSITORIES_PYPI.joinpath("dist")
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

    def list(self, location: Path | None) -> Iterator[ReleaseFileMetadata]:
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
        f"""# this file is generated by {Path(__file__).relative_to(FIXTURE_PATH.parent.parent)}
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
    path = FIXTURE_PATH_REPOSITORIES_LEGACY / f"{metadata.path.name}.html"

    for filepath in [path, *list(path.parent.glob(f"{path.stem}-*.html"))]:
        if not filepath.exists():
            return None

        existing_content = filepath.read_text(encoding="utf-8")

        content = re.sub(
            f"{filepath.name}#sha256=[A-Fa-f0-9]{{64}}",
            f"{filepath.name}#sha256={metadata.sha256}",
            existing_content,
        )
        content = re.sub(
            f'data-dist-info-metadata="sha256=[A-Fa-f0-9]{{64}}">{filepath.name}<',
            f'data-dist-info-metadata="sha256={metadata.sha256}">{filepath.name}<',
            content,
        )
        content = re.sub(
            f"{filepath.name}#md5=[A-Fa-f0-9]{{32}}",
            f"{filepath.name}#md5={metadata.md5}",
            content,
        )
        content = re.sub(
            f'data-dist-info-metadata="md5=[A-Fa-f0-9]{{32}}">{filepath.name}<',
            f'data-dist-info-metadata="md5={metadata.md5}">{filepath.name}<',
            content,
        )

        if existing_content != content:
            logger.info("Rewriting hashes in %s", filepath)
            filepath.write_text(content, encoding="utf-8")


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


class MockedRepositoryFactory:
    def __init__(
        self,
        release_specs: list[ReleaseSpecification],
        project_specs: list[ProjectSpecification],
        pypi: PyPiRepository | None = None,
        refresh: bool = False,
    ) -> None:
        self.pypi = pypi or PyPiRepository(disable_cache=True)
        self.packages: dict[str, MockedProject] = {}
        self.release_specs = release_specs
        self.project_specs = project_specs
        self.refresh = refresh

    def process(self) -> None:
        for file in FIXTURE_PATH_REPOSITORIES_PYPI.joinpath("stubbed").iterdir():
            if file.is_file():
                file.unlink()

        files = []

        for dist in self.release_specs:
            files.extend(self.add_release_file(dist))

        for pkg in self.packages.values():
            pkg.write()

        files.extend(RELEASE_FILE_COLLECTION.list(RELEASE_FILE_LOCATIONS.demo))
        generate_distribution_hashes_fixture(files=files)

    @cached_property
    def known_releases_by_project(self) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}

        for package in self.packages.values():
            if package.name not in result:
                result[package.name] = []

            for release in package.releases:
                result[package.name].append(release.version)

            result[package.name].sort()

        return result

    def clean(self) -> None:
        ignore_missing_files = {
            project.name
            for project in self.project_specs
            if project.ignore_missing_files
        }
        json_fixture_dir = FIXTURE_PATH_REPOSITORIES_PYPI.joinpath("json")

        for file in json_fixture_dir.glob("*.json"):
            if file.stem not in self.packages:
                logger.info(
                    "Removing %s", file.relative_to(FIXTURE_PATH_REPOSITORIES_PYPI)
                )
                file.unlink()
                continue

            package = self.packages[file.stem]

            if package.is_fake:
                continue

            existing_content = file.read_text(encoding="utf-8")
            data = json.loads(existing_content)

            if "versions" in data:
                data["versions"] = self.known_releases_by_project[file.stem]

            if "files" in data and package.name not in ignore_missing_files:
                data["files"] = [
                    _file
                    for _file in data["files"]
                    if RELEASE_FILE_COLLECTION.filename_exists(_file["filename"])
                ]

            content = json.dumps(data, ensure_ascii=False, indent=2)
            if existing_content != content:
                logger.info(
                    "Cleaning up %s", file.relative_to(FIXTURE_PATH_REPOSITORIES_PYPI)
                )
                file.write_text(content + "\n", encoding="utf-8")

        for file in json_fixture_dir.glob("*/*.json"):
            if (
                file.parent.name in self.packages
                and self.packages[file.parent.name].is_fake
            ):
                logger.info(
                    "Skipping clean up for %s (fake)",
                    file.relative_to(FIXTURE_PATH_REPOSITORIES_PYPI),
                )
                continue

            if (
                file.parent.name not in self.packages
                or file.stem not in self.known_releases_by_project[file.parent.stem]
            ):
                logger.info(
                    "Removing %s", file.relative_to(FIXTURE_PATH_REPOSITORIES_PYPI)
                )
                file.unlink()

                if len(list(file.parent.iterdir())) == 0:
                    logger.info(
                        "Removing empty directory %s",
                        file.parent.relative_to(FIXTURE_PATH_REPOSITORIES_PYPI),
                    )
                    file.parent.rmdir()

    def add_release_file(self, spec: ReleaseSpecification) -> list[ReleaseFileMetadata]:
        logger.info("Processing release %s-%s", spec.name, spec.version)

        if spec.name not in self.packages:
            prefer_remote = self.refresh and not spec.is_fake
            self.packages[spec.name] = MockedProject(
                spec.name,
                self.get_json_data(spec.name, None, prefer_remote=prefer_remote),
                is_fake=spec.is_fake,
            )

        package = self.packages[spec.name]
        release = MockedRelease(
            spec.name, spec.version, self.get_json_data(spec.name, spec.version)
        )

        links = (
            []
            if spec.is_fake
            else self.pypi.find_links_for_package(Package(spec.name, spec.version))
        )

        for link in links:
            logger.info("Processing release file %s", link.filename)

            existing_release_file_location = RELEASE_FILE_LOCATIONS.dist.joinpath(
                link.filename
            )
            if existing_release_file_location.exists():
                logger.info(
                    "Release file already exists at %s, skipping",
                    existing_release_file_location.relative_to(
                        FIXTURE_PATH_REPOSITORIES_PYPI
                    ),
                )
                # we do not re-download or stub this
                existing_file = RELEASE_FILE_COLLECTION.find(link.filename)
                assert existing_file is not None
                release.files.append(existing_file)

                continue

            if not spec.stub and link.is_wheel:
                file = self.copy_as_is(link)
            elif link.is_wheel or (link.is_sdist and link.filename.endswith(".zip")):
                file = self.process_zipfile(link)
            else:
                file = self.process_tarfile(link)

            release.add_file(file)

        if not spec.is_fake:
            release.write()

        package.add_release(release)
        return release.files

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

        with self.pypi._cached_or_downloaded_file(link) as src, zipfile.ZipFile(
            dst, "w", compression=zipfile.ZIP_DEFLATED
        ) as stubbed_sdist, zipfile.ZipFile(src) as zf:
            for member in zf.infolist():
                if not is_protected(member.filename):
                    logger.debug("Stubbing file %s(%s)", link.filename, member.filename)
                    stubbed_sdist.writestr(member, io.BytesIO().getvalue())
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

        with self.pypi._cached_or_downloaded_file(link) as src, GzipFile(
            dst.as_posix(), mode="wb", mtime=0
        ) as gz, tarfile.TarFile(
            dst, mode="w", fileobj=gz, format=tarfile.PAX_FORMAT
        ) as dst_tf, tarfile.open(src, "r") as src_tf:
            for member in src_tf.getmembers():
                member.mtime = 0
                member = SdistBuilder.clean_tarinfo(member)

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

    def get_json_data(
        self, name: str, version: str | None, prefer_remote: bool = False
    ) -> dict[str, Any]:
        json_fixture_dir = FIXTURE_PATH_REPOSITORIES_PYPI / "json"

        if version is None:
            path = json_fixture_dir / f"{name}.json"
        else:
            path = json_fixture_dir / name / f"{version}.json"

        data: dict[str, Any] = {}

        if path.exists():
            data = json.loads(path.read_text())

        if prefer_remote and (remote_data := self._get_remote_json_data(name, version)):
            return remote_data

        logger.info(
            "Loading existing json fixture at %s",
            path.relative_to(json_fixture_dir),
        )
        return data

    def _get_remote_json_data(
        self, name: str, version: str | None = None
    ) -> dict[str, Any]:
        if version is None:
            logger.info("Fetching remote json via https://pypi.org/simple/%s", name)
            response = self.pypi._get(
                f"simple/{name}/",
                headers={"Accept": "application/vnd.pypi.simple.v1+json"},
            )
        else:
            logger.info(
                "Fetching remote json via https://pypi.org/pypi/%s/%s/json",
                name,
                version,
            )

            response = self.pypi._get(f"pypi/{name}/{version}/json")

        return response or {}


class MockedJsonFile:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self._content = json.dumps(data, ensure_ascii=False, indent=2)

    @property
    @abstractmethod
    def json_filepath(self) -> Path: ...

    def write(self) -> None:
        self.data.get("info", {"description": ""})["description"] = ""

        if "vulnerabilities" in self.data:
            self.data["vulnerabilities"] = []

        content = json.dumps(self.data, ensure_ascii=False, indent=2)

        if not self.json_filepath.exists() or self._content != content:
            logger.info("Writing json content to %s", self.json_filepath)
            self.json_filepath.parent.mkdir(exist_ok=True)
            self.json_filepath.write_text(content + "\n", encoding="utf-8")
            self._content = content


class MockedRelease(MockedJsonFile):
    def __init__(self, name: str, version: str, data: dict[str, Any]) -> None:
        self.name = name
        self.version = version
        self.files: list[ReleaseFileMetadata] = []
        super().__init__(data=data)

    @property
    def json_filepath(self) -> Path:
        return (
            FIXTURE_PATH_REPOSITORIES_PYPI / "json" / self.name / f"{self.version}.json"
        )

    def add_file(self, metadata: ReleaseFileMetadata) -> None:
        self.files.append(metadata)

        for item in self.data["urls"]:
            if item["filename"] == metadata.path.name:
                item["digests"] = {"md5": metadata.md5, "sha256": metadata.sha256}
                item["md5_digest"] = metadata.md5


class MockedProject(MockedJsonFile):
    def __init__(self, name: str, data: dict[str, Any], is_fake: bool = False) -> None:
        self.name = name
        self.releases: list[MockedRelease] = []
        self.is_fake: bool = is_fake
        super().__init__(data=data)

    @property
    def json_filepath(self) -> Path:
        return FIXTURE_PATH_REPOSITORIES_PYPI / "json" / f"{self.name}.json"

    def add_release(self, release: MockedRelease) -> None:
        self.releases.append(release)

        if self.is_fake:
            return

        for file in release.files:
            for item in self.data.get("files", []):
                if item["filename"] == file.path.name:
                    item["hashes"] = {"md5": file.md5, "sha256": file.sha256}

            cleanup_legacy_html_hashes(file)
            cleanup_installation_fixtures(file)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MockedProject):
            return self.name == other.name

        if isinstance(other, str):
            return self.name == other

        return False


if __name__ == "__main__":
    factory = MockedRepositoryFactory(
        RELEASE_SPECS, PROJECT_SPECS, PyPiRepository(disable_cache=True), refresh=False
    )
    factory.process()
    factory.clean()
