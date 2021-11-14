import logging

from pathlib import Path
from typing import TYPE_CHECKING
from typing import List
from typing import Optional
from typing import Union

from ..utils.authenticator import Authenticator
from ..utils.helpers import get_cert
from ..utils.helpers import get_client_cert
from .uploader import Uploader


if TYPE_CHECKING:
    from cleo.io import BufferedIO
    from cleo.io import ConsoleIO

    from ..poetry import Poetry

logger = logging.getLogger(__name__)


class Publisher:
    """
    Registers and publishes packages to remote repositories.
    """

    def __init__(self, poetry: "Poetry", io: Union["BufferedIO", "ConsoleIO"]) -> None:
        self._poetry = poetry
        self._package = poetry.package
        self._io = io
        self._uploader = Uploader(poetry, io)
        self._authenticator = Authenticator(poetry.config, self._io)

    @property
    def files(self) -> List[Path]:
        return self._uploader.files

    def publish(
        self,
        repository_name: Optional[str],
        username: Optional[str],
        password: Optional[str],
        cert: Optional[Path] = None,
        client_cert: Optional[Path] = None,
        dry_run: Optional[bool] = False,
    ) -> None:
        if not repository_name:
            url = "https://upload.pypi.org/legacy/"
            repository_name = "pypi"
        else:
            # Retrieving config information
            url = self._poetry.config.get(f"repositories.{repository_name}.url")
            if url is None:
                raise RuntimeError(f"Repository {repository_name} is not defined")

        if not (username and password):
            # Check if we have a token first
            token = self._authenticator.get_pypi_token(repository_name)
            if token:
                logger.debug(f"Found an API token for {repository_name}.")
                username = "__token__"
                password = token
            else:
                auth = self._authenticator.get_http_auth(repository_name)
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
