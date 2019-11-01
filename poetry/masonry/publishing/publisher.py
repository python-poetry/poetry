import logging

from poetry.utils.helpers import get_cert
from poetry.utils.helpers import get_client_cert
from poetry.utils.helpers import get_http_basic_auth

from .uploader import Uploader


logger = logging.getLogger(__name__)


class Publisher:
    """
    Registers and publishes packages to remote repositories.
    """

    def __init__(self, poetry, io):
        self._poetry = poetry
        self._package = poetry.package
        self._io = io
        self._uploader = Uploader(poetry, io)

    @property
    def files(self):
        return self._uploader.files

    def publish(self, repository_name, username, password, cert=None, client_cert=None):
        if repository_name:
            self._io.write_line(
                "Publishing <c1>{}</c1> (<b>{}</b>) "
                "to <info>{}</info>".format(
                    self._package.pretty_name,
                    self._package.pretty_version,
                    repository_name,
                )
            )
        else:
            self._io.write_line(
                "Publishing <c1>{}</c1> (<b>{}</b>) "
                "to <info>PyPI</info>".format(
                    self._package.pretty_name, self._package.pretty_version
                )
            )

        if not repository_name:
            url = "https://upload.pypi.org/legacy/"
            repository_name = "pypi"
        else:
            # Retrieving config information
            repository = self._poetry.config.get(
                "repositories.{}".format(repository_name)
            )
            if repository is None:
                raise RuntimeError(
                    "Repository {} is not defined".format(repository_name)
                )

            url = repository["url"]

        if not (username and password):
            # Check if we have a token first
            token = self._poetry.config.get("pypi-token.{}".format(repository_name))
            if token:
                logger.debug("Found an API token for {}.".format(repository_name))
                username = "__token__"
                password = token
            else:
                auth = get_http_basic_auth(self._poetry.config, repository_name)
                if auth:
                    logger.debug(
                        "Found authentication information for {}.".format(
                            repository_name
                        )
                    )
                    username = auth[0]
                    password = auth[1]

        resolved_client_cert = client_cert or get_client_cert(
            self._poetry.config, repository_name
        )
        # Requesting missing credentials but only if there is not a client cert defined.
        if not resolved_client_cert:
            if username is None:
                username = self._io.ask("Username:")

            if password is None:
                password = self._io.ask_hidden("Password:")

        self._uploader.auth(username, password)

        return self._uploader.upload(
            url,
            cert=cert or get_cert(self._poetry.config, repository_name),
            client_cert=resolved_client_cert,
        )
