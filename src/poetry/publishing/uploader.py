from __future__ import annotations

import tarfile
import zipfile

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Literal

import requests

from packaging.metadata import RawMetadata
from packaging.metadata import parse_email
from poetry.core.masonry.utils.helpers import distribution_name
from requests_toolbelt import user_agent
from requests_toolbelt.multipart import MultipartEncoder
from requests_toolbelt.multipart import MultipartEncoderMonitor

from poetry.__version__ import __version__
from poetry.publishing.hash_manager import HashManager
from poetry.utils.constants import REQUESTS_TIMEOUT
from poetry.utils.patterns import wheel_file_re


if TYPE_CHECKING:
    from cleo.io.io import IO

    from poetry.poetry import Poetry


class UploadError(Exception):
    pass


class Uploader:
    def __init__(self, poetry: Poetry, io: IO, dist_dir: Path | None = None) -> None:
        self._poetry = poetry
        self._package = poetry.package
        self._io = io
        self._dist_dir = dist_dir or self.default_dist_dir
        self._username: str | None = None
        self._password: str | None = None

    @property
    def user_agent(self) -> str:
        agent: str = user_agent("poetry", __version__)
        return agent

    @property
    def default_dist_dir(self) -> Path:
        return self._poetry.file.path.parent / "dist"

    @property
    def dist_dir(self) -> Path:
        if not self._dist_dir.is_absolute():
            return self._poetry.file.path.parent / self._dist_dir

        return self._dist_dir

    @property
    def files(self) -> list[Path]:
        dist = self.dist_dir
        version = self._package.version.to_string()
        escaped_name = distribution_name(self._package.name)

        wheels = list(dist.glob(f"{escaped_name}-{version}-*.whl"))
        tars = list(dist.glob(f"{escaped_name}-{version}.tar.gz"))

        return sorted(wheels + tars)

    def auth(self, username: str | None, password: str | None) -> None:
        self._username = username
        self._password = password

    def make_session(self) -> requests.Session:
        session = requests.Session()
        auth = self.get_auth()
        if auth is not None:
            session.auth = auth

        session.headers["User-Agent"] = self.user_agent
        return session

    def get_auth(self) -> tuple[str, str] | None:
        if self._username is None or self._password is None:
            return None

        return (self._username, self._password)

    def upload(
        self,
        url: str,
        cert: Path | bool = True,
        client_cert: Path | None = None,
        dry_run: bool = False,
        skip_existing: bool = False,
    ) -> None:
        session = self.make_session()

        session.verify = str(cert) if isinstance(cert, Path) else cert

        if client_cert:
            session.cert = str(client_cert)

        with session:
            self._upload(session, url, dry_run, skip_existing)

    @classmethod
    def post_data(cls, file: Path) -> dict[str, Any]:
        file_type = cls._get_type(file)

        hash_manager = HashManager()
        hash_manager.hash(file)
        file_hashes = hash_manager.hexdigest()

        md5_digest = file_hashes.md5
        sha2_digest = file_hashes.sha256
        blake2_256_digest = file_hashes.blake2_256

        py_version: str | None = None
        if file_type == "bdist_wheel":
            wheel_info = wheel_file_re.match(file.name)
            if wheel_info is not None:
                py_version = wheel_info.group("pyver")
        else:
            py_version = "source"

        data: dict[str, Any] = {
            # Upload API (https://docs.pypi.org/api/upload/)
            # ":action", "protocol_version" and "content are added later
            "md5_digest": md5_digest,
            "sha256_digest": sha2_digest,
            "blake2_256_digest": blake2_256_digest,
            "filetype": file_type,
            "pyversion": py_version,
        }

        for key, value in cls._get_metadata(file).items():
            # strip trailing 's' to match API field names
            # see https://docs.pypi.org/api/upload/
            if key in {"platforms", "supported_platforms", "license_files"}:
                key = key[:-1]

            # revert some special cases from packaging.metadata.parse_email()

            # "keywords" is not "multiple use" but a comma-separated string
            if key == "keywords":
                assert isinstance(value, list)
                value = ", ".join(value)

            # "project_urls" is not a dict
            if key == "project_urls":
                assert isinstance(value, dict)
                value = [f"{k}, {v}" for k, v in value.items()]

            data[key] = value

        return data

    def _upload(
        self,
        session: requests.Session,
        url: str,
        dry_run: bool = False,
        skip_existing: bool = False,
    ) -> None:
        for file in self.files:
            self._upload_file(session, url, file, dry_run, skip_existing)

    def _upload_file(
        self,
        session: requests.Session,
        url: str,
        file: Path,
        dry_run: bool = False,
        skip_existing: bool = False,
    ) -> None:
        from cleo.ui.progress_bar import ProgressBar

        if not file.is_file():
            raise UploadError(f"Archive ({file}) does not exist")

        data = self.post_data(file)
        data.update({":action": "file_upload", "protocol_version": "1"})

        data_to_send: list[tuple[str, Any]] = self._prepare_data(data)

        with file.open("rb") as fp:
            data_to_send.append(
                ("content", (file.name, fp, "application/octet-stream"))
            )
            encoder = MultipartEncoder(data_to_send)
            bar = ProgressBar(self._io, max=encoder.len)
            bar.set_format(f" - Uploading <c1>{file.name}</c1> <b>%percent%%</b>")
            monitor = MultipartEncoderMonitor(
                encoder, lambda monitor: bar.set_progress(monitor.bytes_read)
            )

            bar.start()

            resp = None

            try:
                if not dry_run:
                    resp = session.post(
                        url,
                        data=monitor,
                        allow_redirects=False,
                        headers={"Content-Type": monitor.content_type},
                        timeout=REQUESTS_TIMEOUT,
                    )
                if resp is None or 200 <= resp.status_code < 300:
                    bar.set_format(
                        f" - Uploading <c1>{file.name}</c1> <fg=green>%percent%%</>"
                    )
                    bar.finish()
                elif 300 <= resp.status_code < 400:
                    if self._io.output.is_decorated():
                        self._io.overwrite(
                            f" - Uploading <c1>{file.name}</c1> <error>FAILED</>"
                        )
                    raise UploadError(
                        "Redirects are not supported. "
                        "Is the URL missing a trailing slash?"
                    )
                elif resp.status_code == 400 and "was ever registered" in resp.text:
                    self._register(session, url)
                    resp.raise_for_status()
                elif skip_existing and self._is_file_exists_error(resp):
                    bar.set_format(
                        f" - Uploading <c1>{file.name}</c1> <warning>File exists."
                        " Skipping</>"
                    )
                    bar.display()
                else:
                    resp.raise_for_status()

            except requests.RequestException as e:
                if self._io.output.is_decorated():
                    self._io.overwrite(
                        f" - Uploading <c1>{file.name}</c1> <error>FAILED</>"
                    )

                if e.response is not None:
                    message = (
                        f"HTTP Error {e.response.status_code}: "
                        f"{e.response.reason} | {e.response.content!r}"
                    )
                    raise UploadError(message) from e

                raise UploadError("Error connecting to repository") from e

            finally:
                self._io.write_line("")

    def _register(self, session: requests.Session, url: str) -> requests.Response:
        """
        Register a package to a repository.
        """
        dist = self.dist_dir
        escaped_name = distribution_name(self._package.name)
        file = dist / f"{escaped_name}-{self._package.version.to_string()}.tar.gz"

        if not file.exists():
            raise RuntimeError(f'"{file.name}" does not exist.')

        data = self.post_data(file)
        data.update({":action": "submit", "protocol_version": "1"})

        data_to_send = self._prepare_data(data)
        encoder = MultipartEncoder(data_to_send)
        resp = session.post(
            url,
            data=encoder,
            allow_redirects=False,
            headers={"Content-Type": encoder.content_type},
            timeout=REQUESTS_TIMEOUT,
        )

        resp.raise_for_status()

        return resp

    def _prepare_data(self, data: dict[str, Any]) -> list[tuple[str, str]]:
        data_to_send = []
        for key, value in data.items():
            if not isinstance(value, (list, tuple)):
                data_to_send.append((key, value))
            else:
                for item in value:
                    data_to_send.append((key, item))

        return data_to_send

    @staticmethod
    def _get_type(file: Path) -> Literal["bdist_wheel", "sdist"]:
        exts = file.suffixes
        if exts and exts[-1] == ".whl":
            return "bdist_wheel"
        elif len(exts) >= 2 and "".join(exts[-2:]) == ".tar.gz":
            return "sdist"

        raise ValueError("Unknown distribution format " + "".join(exts))

    @staticmethod
    def _get_metadata(file: Path) -> RawMetadata:
        if file.suffix == ".whl":
            with zipfile.ZipFile(file) as z:
                for name in z.namelist():
                    parts = Path(name).parts
                    if (
                        len(parts) == 2
                        and parts[1] == "METADATA"
                        and parts[0].endswith(".dist-info")
                    ):
                        with z.open(name) as mf:
                            return parse_email(mf.read().decode("utf-8"))[0]
            raise FileNotFoundError("METADATA not found in wheel")

        elif file.suffixes[-2:] == [".tar", ".gz"]:
            with tarfile.open(file, "r:gz") as tar:
                for member in tar.getmembers():
                    parts = Path(member.name).parts
                    if (
                        len(parts) == 2
                        and parts[1] == "PKG-INFO"
                        and (pf := tar.extractfile(member))
                    ):
                        return parse_email(pf.read().decode("utf-8"))[0]
            raise FileNotFoundError("PKG-INFO not found in sdist")

        raise ValueError(f"Unsupported file type: {file}")

    def _is_file_exists_error(self, response: requests.Response) -> bool:
        # based on https://github.com/pypa/twine/blob/a6dd69c79f7b5abfb79022092a5d3776a499e31b/twine/commands/upload.py#L32
        status = response.status_code
        reason = response.reason.lower()
        text = response.text.lower()
        reason_and_text = reason + text

        return (
            # pypiserver (https://pypi.org/project/pypiserver)
            status == 409
            # PyPI / TestPyPI / GCP Artifact Registry
            or (status == 400 and "already exist" in reason_and_text)
            # Nexus Repository OSS (https://www.sonatype.com/nexus-repository-oss)
            or (status == 400 and "updating asset" in reason_and_text)
            or (status == 400 and "cannot be updated" in reason_and_text)
            # Artifactory (https://jfrog.com/artifactory/)
            or (status == 403 and "overwrite artifact" in reason_and_text)
            # Gitlab Enterprise Edition (https://about.gitlab.com)
            or (status == 400 and "already been taken" in reason_and_text)
        )
