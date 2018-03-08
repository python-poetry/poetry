# -*- coding: utf-8 -*-

import toml
import twine.utils

from pathlib import Path

from requests.exceptions import HTTPError
from twine.commands.upload import find_dists, skip_upload
from twine.repository import Repository as BaseRepository
from twine.exceptions import PackageNotFound, RedirectDetected
from twine.package import PackageFile
from requests_toolbelt.multipart import (
    MultipartEncoder, MultipartEncoderMonitor
)

from poetry.locations import CONFIG_DIR


class Repository(BaseRepository):

    def __init__(self, io, url, username, password):
        self._io = io

        super(Repository, self).__init__(url, username, password)

    def register(self, package):
        data = package.metadata_dictionary()
        data.update({
            ":action": "submit",
            "protocol_version": "1",
        })

        self._io.writeln(
            " - Registering <info>{0}</>".format(package.basefilename)
        )

        data_to_send = self._convert_data_to_list_of_tuples(data)
        encoder = MultipartEncoder(data_to_send)
        resp = self.session.post(
            self.url,
            data=encoder,
            allow_redirects=False,
            headers={'Content-Type': encoder.content_type}
        )
        # Bug 28. Try to silence a ResourceWarning by releasing the socket.
        resp.close()

        return resp

    def _upload(self, package):
        data = package.metadata_dictionary()
        data.update({
            # action
            ":action": "file_upload",
            "protocol_version": "1",
        })

        data_to_send = self._convert_data_to_list_of_tuples(data)

        with open(package.filename, "rb") as fp:
            data_to_send.append((
                "content",
                (package.basefilename, fp, "application/octet-stream"),
            ))
            encoder = MultipartEncoder(data_to_send)
            bar = self._io.create_progress_bar(encoder.len)
            bar.set_format(
                " - Uploading <info>{0}</> <comment>%percent%%</>".format(
                    package.basefilename
                )
            )
            monitor = MultipartEncoderMonitor(
                encoder, lambda monitor: bar.set_progress(monitor.bytes_read)
            )

            bar.start()

            resp = self.session.post(
                self.url,
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


class Publisher(object):
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

        repository = Repository(self._io, url, username, password)

        # TODO: handle certificates

        self.upload(repository)

    def register(self, repository):
        """
        Register a package to a repository.
        """
        dist = self._poetry.file.parent / 'dist'
        package = dist / f'{self._package.name}-{self._package.version}.tar.gz'

        if package.exists():
            raise PackageNotFound(
                '"{0}" does not exist on the file system.'.format(package)
            )

        resp = repository.register(
            PackageFile.from_filename(str(package), None)
        )

        repository.close()

        if resp.is_redirect:
            raise RedirectDetected(
                ('"{0}" attempted to redirect to "{1}" during registration.'
                 ' Aborting...').format(repository.url,
                                        resp.headers["location"]))

        resp.raise_for_status()

    def upload(self, repository):
        """
        Upload packages for the current project.
        """
        try:
            self._upload(repository)
        except HTTPError as e:
            if (
                e.response.status_code not in (403, 400)
                or e.response.status_code == 400 and 'was ever registered' not in e.response.text
            ):
                raise

            # It may be the first time we publish the package
            # We'll try to register it and go from there
            try:
                self.register(repository)
            except HTTPError:
                raise

    def _upload(self, repository):
        skip_existing = False
        dist = self._poetry.file.parent / 'dist'
        packages = list(dist.glob(f'{self._package.name}-{self._package.version}*'))
        dists = find_dists([str(p) for p in packages])
        uploads = [i for i in dists if not i.endswith(".asc")]

        for filename in uploads:
            package = PackageFile.from_filename(filename, None)
            skip_message = (
                " - Skipping <comment>{0}</> because it appears to already exist"
                .format(
                    package.basefilename
                )
            )

            # Note: The skip_existing check *needs* to be first, because otherwise
            #       we're going to generate extra HTTP requests against a hardcoded
            #       URL for no reason.
            if skip_existing and repository.package_is_uploaded(package):
                self._io.writeln(skip_message)
                continue

            resp = repository.upload(package)

            # Bug 92. If we get a redirect we should abort because something seems
            # funky. The behaviour is not well defined and redirects being issued
            # by PyPI should never happen in reality. This should catch malicious
            # redirects as well.
            if resp.is_redirect:
                raise RedirectDetected(
                    ('"{0}" attempted to redirect to "{1}" during upload.'
                     ' Aborting...').format(repository.url,
                                            resp.headers["location"]))

            if skip_upload(resp, skip_existing, package):
                self._io.writeln(skip_message)

                continue

            twine.utils.check_status_code(resp)

        # Bug 28. Try to silence a ResourceWarning by clearing the connection
        # pool.
        repository.close()

