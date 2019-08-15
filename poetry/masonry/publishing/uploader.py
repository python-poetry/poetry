import hashlib
import io
import math
import re

from typing import List

import requests

from requests import adapters
from requests.exceptions import HTTPError
from requests.packages.urllib3 import util
from requests_toolbelt import user_agent
from requests_toolbelt.multipart import MultipartEncoder, MultipartEncoderMonitor

from poetry.__version__ import __version__
from poetry.utils.helpers import normalize_version
from poetry.utils.patterns import wheel_file_re

from ..metadata import Metadata


_has_blake2 = hasattr(hashlib, "blake2b")


class UploadError(Exception):
    def __init__(self, error):  # type: (HTTPError) -> None
        super(UploadError, self).__init__(
            "HTTP Error {}: {}".format(
                error.response.status_code, error.response.reason
            )
        )


class Uploader:
    def __init__(self, poetry, io):
        self._poetry = poetry
        self._package = poetry.package
        self._io = io
        self._username = None
        self._password = None

    @property
    def user_agent(self):
        return user_agent("poetry", __version__)

    @property
    def adapter(self):
        retry = util.Retry(
            connect=5,
            total=10,
            method_whitelist=["GET"],
            status_forcelist=[500, 501, 502, 503],
        )

        return adapters.HTTPAdapter(max_retries=retry)

    @property
    def files(self):  # type: () -> List[str]
        dist = self._poetry.file.parent / "dist"
        version = normalize_version(self._package.version.text)

        wheels = list(
            dist.glob(
                "{}-{}-*.whl".format(
                    re.sub(
                        r"[^\w\d.]+", "_", self._package.pretty_name, flags=re.UNICODE
                    ),
                    re.sub(r"[^\w\d.]+", "_", version, flags=re.UNICODE),
                )
            )
        )
        tars = list(
            dist.glob("{}-{}.tar.gz".format(self._package.pretty_name, version))
        )

        return sorted(wheels + tars)

    def auth(self, username, password):
        self._username = username
        self._password = password

    def make_session(self):
        session = requests.session()
        if self.is_authenticated():
            session.auth = (self._username, self._password)

        session.headers["User-Agent"] = self.user_agent
        for scheme in ("http://", "https://"):
            session.mount(scheme, self.adapter)

        return session

    def is_authenticated(self):
        return self._username is not None and self._password is not None

    def upload(self, url):
        session = self.make_session()

        try:
            self._upload(session, url)
        finally:
            session.close()

    def post_data(self, file):
        meta = Metadata.from_package(self._package)

        file_type = self._get_type(file)

        if _has_blake2:
            blake2_256_hash = hashlib.blake2b(digest_size=256 // 8)

        md5_hash = hashlib.md5()
        sha256_hash = hashlib.sha256()
        with file.open("rb") as fp:
            for content in iter(lambda: fp.read(io.DEFAULT_BUFFER_SIZE), b""):
                md5_hash.update(content)
                sha256_hash.update(content)

                if _has_blake2:
                    blake2_256_hash.update(content)

        md5_digest = md5_hash.hexdigest()
        sha2_digest = sha256_hash.hexdigest()
        if _has_blake2:
            blake2_256_digest = blake2_256_hash.hexdigest()
        else:
            blake2_256_digest = None

        if file_type == "bdist_wheel":
            wheel_info = wheel_file_re.match(file.name)
            py_version = wheel_info.group("pyver")
        else:
            py_version = None

        data = {
            # identify release
            "name": meta.name,
            "version": meta.version,
            # file content
            "filetype": file_type,
            "pyversion": py_version,
            # additional meta-data
            "metadata_version": meta.metadata_version,
            "summary": meta.summary,
            "home_page": meta.home_page,
            "author": meta.author,
            "author_email": meta.author_email,
            "maintainer": meta.maintainer,
            "maintainer_email": meta.maintainer_email,
            "license": meta.license,
            "description": meta.description,
            "keywords": meta.keywords,
            "platform": meta.platforms,
            "classifiers": meta.classifiers,
            "download_url": meta.download_url,
            "supported_platform": meta.supported_platforms,
            "comment": None,
            "md5_digest": md5_digest,
            "sha256_digest": sha2_digest,
            "blake2_256_digest": blake2_256_digest,
            # PEP 314
            "provides": meta.provides,
            "requires": meta.requires,
            "obsoletes": meta.obsoletes,
            # Metadata 1.2
            "project_urls": meta.project_urls,
            "provides_dist": meta.provides_dist,
            "obsoletes_dist": meta.obsoletes_dist,
            "requires_dist": meta.requires_dist,
            "requires_external": meta.requires_external,
            "requires_python": meta.requires_python,
        }

        # Metadata 2.1
        if meta.description_content_type:
            data["description_content_type"] = meta.description_content_type

        # TODO: Provides extra

        return data

    def _upload(self, session, url):
        try:
            self._do_upload(session, url)
        except HTTPError as e:
            if (
                e.response.status_code == 400
                and "was ever registered" in e.response.text
            ):
                try:
                    self._register(session, url)
                except HTTPError as e:
                    raise UploadError(e)

            raise UploadError(e)

    def _do_upload(self, session, url):
        for file in self.files:
            # TODO: Check existence

            resp = self._upload_file(session, url, file)

            resp.raise_for_status()

    def _upload_file(self, session, url, file):
        data = self.post_data(file)
        data.update(
            {
                # action
                ":action": "file_upload",
                "protocol_version": "1",
            }
        )

        data_to_send = self._prepare_data(data)

        with file.open("rb") as fp:
            data_to_send.append(
                ("content", (file.name, fp, "application/octet-stream"))
            )
            encoder = MultipartEncoder(data_to_send)
            bar = self._io.create_progress_bar(encoder.len)
            bar.set_format(
                " - Uploading <info>{0}</> <comment>%percent%%</>".format(file.name)
            )
            monitor = MultipartEncoderMonitor(
                encoder, lambda monitor: bar.set_progress(monitor.bytes_read)
            )

            bar.start()

            resp = session.post(
                url,
                data=monitor,
                allow_redirects=False,
                headers={"Content-Type": monitor.content_type},
            )

            if resp.ok:
                bar.finish()

                self._io.writeln("")
            else:
                if self._io.output.is_decorated():
                    self._io.overwrite(
                        " - Uploading <info>{0}</> <error>{1}%</>".format(
                            file.name, int(math.floor(bar._percent * 100))
                        )
                    )
                else:
                    self._io.writeln("")

        return resp

    def _register(self, session, url):
        """
        Register a package to a repository.
        """
        dist = self._poetry.file.parent / "dist"
        file = dist / "{}-{}.tar.gz".format(
            self._package.name, normalize_version(self._package.version.text)
        )

        if not file.exists():
            raise RuntimeError('"{0}" does not exist.'.format(file.name))

        data = self.post_data(file)
        data.update({":action": "submit", "protocol_version": "1"})

        data_to_send = self._prepare_data(data)
        encoder = MultipartEncoder(data_to_send)
        resp = session.post(
            url,
            data=encoder,
            allow_redirects=False,
            headers={"Content-Type": encoder.content_type},
        )

        resp.raise_for_status()

        return resp

    def _prepare_data(self, data):
        data_to_send = []
        for key, value in data.items():
            if not isinstance(value, (list, tuple)):
                data_to_send.append((key, value))
            else:
                for item in value:
                    data_to_send.append((key, item))

        return data_to_send

    def _get_type(self, file):
        exts = file.suffixes
        if exts[-1] == ".whl":
            return "bdist_wheel"
        elif len(exts) >= 2 and "".join(exts[-2:]) == ".tar.gz":
            return "sdist"

        raise ValueError("Unknown distribution format {}".format("".join(exts)))
