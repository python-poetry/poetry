import logging

from typing import Optional

from poetry.utils._compat import Path
from poetry.utils.helpers import get_cert
from poetry.utils.helpers import get_client_cert
from poetry.utils.password_manager import PasswordManager

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
        self._password_manager = PasswordManager(poetry.config)

    @property
    def files(self):
        return self._uploader.files

    def publish(
        self,
        repository_name,
        username,
        password,
        cert=None,
        client_cert=None,
        dry_run=False,
    ):  # type: (Optional[str], Optional[str], Optional[str], Optional[Path], Optional[Path], Optional[bool]) -> None
        if not repository_name:
            url = "https://upload.pypi.org/legacy/"
            repository_name = "pypi"
        else:
            # Retrieving config information
            url = self._poetry.config.get("repositories.{}.url".format(repository_name))
            if url is None:
                raise RuntimeError(
                    "Repository {} is not defined".format(repository_name)
                )

        if not (username and password):
            # Check if we have a token first
            token = self._password_manager.get_pypi_token(repository_name)
            if token:
                logger.debug("Found an API token for {}.".format(repository_name))
                username = "__token__"
                password = token
            else:
                auth = self._password_manager.get_http_auth(repository_name)
                if auth:
                    logger.debug(
                        "Found authentication information for {}.".format(
                            repository_name
                        )
                    )
                    username = auth["username"]
                    password = auth["password"]

        resolved_client_cert = client_cert or get_client_cert(
            self._poetry.config, repository_name
        )
        # Requesting missing credentials but only if there is not a client cert defined.
        if not resolved_client_cert:
            if username is None:
                username = self._io.ask("Username:")

            # skip password input if no username is provided, assume unauthenticated
            if username and password is None:
                password = self._io.ask_hidden("Password:")

        self._uploader.auth(username, password)

        self._io.write_line(
            "Publishing <c1>{}</c1> (<c2>{}</c2>) "
            "to <info>{}</info>".format(
                self._package.pretty_name,
                self._package.pretty_version,
                "PyPI" if repository_name == "pypi" else repository_name,
            )
        )

        self._uploader.upload(
            url,
            cert=cert or get_cert(self._poetry.config, repository_name),
            client_cert=resolved_client_cert,
            dry_run=dry_run,
        )
