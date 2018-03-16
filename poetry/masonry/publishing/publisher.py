import hashlib
import io
import re

import requests
import toml

from pathlib import Path

from requests import adapters
from requests.exceptions import HTTPError
from requests.packages.urllib3 import util
from requests_toolbelt import user_agent
from requests_toolbelt.multipart import (
    MultipartEncoder, MultipartEncoderMonitor
)

from poetry import __version__
from poetry.locations import CONFIG_DIR

from ..metadata import Metadata


wheel_file_re = re.compile(
    r"""^(?P<namever>(?P<name>.+?)(-(?P<ver>\d.+?))?)
        ((-(?P<build>\d.*?))?-(?P<pyver>.+?)-(?P<abi>.+?)-(?P<plat>.+?)
        \.whl|\.dist-info)$""",
    re.VERBOSE
)

KEYWORDS_TO_NOT_FLATTEN = {'gpg_signature', 'content'}


class Publisher:
    """
    Registers and publishes packages to remote repositories.
    """

    def __init__(self, poetry, io):
        self._poetry = poetry
        self._package = poetry.package
        self._io = io

    def publish(self, repository_name):
        if repository_name:
            self._io.writeln(
                f'Publishing <info>{self._package.pretty_name}</info> '
                f'(<comment>{self._package.pretty_version}</comment>) '
                f'to <fg=cyan>{repository_name}</>'
            )
        else:
            self._io.writeln(
                f'Publishing <info>{self._package.pretty_name}</info> '
                f'(<comment>{self._package.pretty_version}</comment>) '
                f'to <fg=cyan>PyPI</>'
            )

        if not repository_name:
            url = 'https://upload.pypi.org/legacy/'
            repository_name = 'pypi'
        else:
            # Retrieving config information
            config_file = Path(CONFIG_DIR) / 'config.toml'

            if not config_file.exists():
                raise RuntimeError(
                    'Config file does not exist. '
                    'Unable to get repository information'
                )

            with config_file.open() as f:
                config = toml.loads(f.read())

            if (
                'repositories' not in config
                or repository_name not in config['repositories']
            ):
                raise RuntimeError(
                    f'Repository {repository_name} is not defined'
                )

            url = config['repositories'][repository_name]['url']

        username = None
        password = None
        auth_file = Path(CONFIG_DIR) / 'auth.toml'
        if auth_file.exists():
            with auth_file.open() as f:
                auth_config = toml.loads(f.read())

            if 'http-basic' in auth_config and repository_name in auth_config['http-basic']:
                config = auth_config['http-basic'][repository_name]

                username = config.get('username')
                password = config.get('password')

        # Requesting missing credentials
        if not username:
            username = self._io.ask('Username:')

        if not password:
            password = self._io.ask_hidden('Password:')

        session = requests.session()
        session.auth = (username, password)
        session.headers['User-Agent'] = self._make_user_agent_string()
        for scheme in ('http://', 'https://'):
            session.mount(scheme, self._make_adapter_with_retries())

        # TODO: handle certificates

        try:
            self.upload(session, url)
        finally:
            session.close()

    def register(self, session, url):
        """
        Register a package to a repository.
        """
        dist = self._poetry.file.parent / 'dist'
        file = dist / f'{self._package.name}-{self._package.version}.tar.gz'

        if not file.exists():
            raise RuntimeError(
                '"{0}" does not exist on the file system.'.format(file.name)
            )

        data = self.post_data(file)
        data.update({
            ":action": "submit",
            "protocol_version": "1",
        })

        data_to_send = self._convert_data_to_list_of_tuples(data)
        encoder = MultipartEncoder(data_to_send)
        resp = session.post(
            url,
            data=encoder,
            allow_redirects=False,
            headers={'Content-Type': encoder.content_type},
        )

        return resp

    def upload(self, session, url):
        """
        Upload packages for the current project.
        """
        try:
            self._upload(session, url)
        except HTTPError as e:
            if (
                e.response.status_code not in (403, 400)
                or e.response.status_code == 400 and 'was ever registered' not in e.response.text
            ):
                raise

            # It may be the first time we publish the package
            # We'll try to register it and go from there
            try:
                self.register(session, url)
            except HTTPError:
                raise

    def post_data(self, file):
        meta = Metadata.from_package(self._package)

        file_type = self._get_type(file)

        blake2_256_hash = hashlib.blake2b(digest_size=256 // 8)
        md5_hash = hashlib.md5()
        sha2_hash = hashlib.sha256()
        with file.open('rb') as fp:
            for content in iter(lambda: fp.read(io.DEFAULT_BUFFER_SIZE), b''):
                md5_hash.update(content)
                sha2_hash.update(content)
                blake2_256_hash.update(content)

        md5_digest = md5_hash.hexdigest()
        sha2_digest = sha2_hash.hexdigest()
        blake2_256_digest = blake2_256_hash.hexdigest()

        if file_type == 'bdist_wheel':
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
            data['description_content_type'] = meta.description_content_type

        # TODO: Provides extra

        return data

    def _upload(self, session, url):
        dist = self._poetry.file.parent / 'dist'
        packages = dist.glob(f'{self._package.name}-{self._package.version}*')
        files = (
            i for i in packages if (
                i.match(f'{self._package.name}-{self._package.version}-*.whl')
                or
                i.match(f'{self._package.name}-{self._package.version}.tar.gz')
            )
        )

        for file in files:
            # TODO: Check existence

            resp = self._upload_file(session, url, file)

            # Bug 92. If we get a redirect we should abort because something seems
            # funky. The behaviour is not well defined and redirects being issued
            # by PyPI should never happen in reality. This should catch malicious
            # redirects as well.
            if resp.is_redirect:
                raise RuntimeError(
                    ('"{0}" attempted to redirect to "{1}" during upload.'
                     ' Aborting...').format(url, resp.headers["location"]))

            resp.raise_for_status()

    def _upload_file(self, session, url, file):
        data = self.post_data(file)
        data.update({
            # action
            ":action": "file_upload",
            "protocol_version": "1",
        })

        data_to_send = self._convert_data_to_list_of_tuples(data)

        with file.open('rb') as fp:
            data_to_send.append((
                "content",
                (file.name, fp, "application/octet-stream"),
            ))
            encoder = MultipartEncoder(data_to_send)
            bar = self._io.create_progress_bar(encoder.len)
            bar.set_format(
                " - Uploading <info>{0}</> <comment>%percent%%</>".format(
                    file.name
                )
            )
            monitor = MultipartEncoderMonitor(
                encoder, lambda monitor: bar.set_progress(monitor.bytes_read)
            )

            bar.start()

            resp = session.post(
                url,
                data=monitor,
                allow_redirects=False,
                headers={'Content-Type': monitor.content_type}
            )

            if resp.ok:
                bar.finish()

                self._io.writeln('')
            else:
                self._io.overwrite('')

        return resp

    def _convert_data_to_list_of_tuples(self, data):
        data_to_send = []
        for key, value in data.items():
            if (key in KEYWORDS_TO_NOT_FLATTEN or
                    not isinstance(value, (list, tuple))):
                data_to_send.append((key, value))
            else:
                for item in value:
                    data_to_send.append((key, item))
        return data_to_send

    def _get_type(self, file):
        exts = file.suffixes
        if exts[-1] == '.whl':
            return 'bdist_wheel'
        elif len(exts) >= 2 and ''.join(exts[-2:]) == '.tar.gz':
            return 'sdist'

        raise ValueError(
            f'Unknown distribution format {"".join(exts)}'
        )

    @staticmethod
    def _make_adapter_with_retries():
        retry = util.Retry(
            connect=5,
            total=10,
            method_whitelist=['GET'],
            status_forcelist=[500, 501, 502, 503],
        )
        return adapters.HTTPAdapter(max_retries=retry)

    @staticmethod
    def _make_user_agent_string():
        return user_agent(
            'twine', __version__,
        )
