import logging

from typing import TYPE_CHECKING
from typing import List
from typing import Optional
from typing import Union

from poetry.publishing.uploader import Uploader
from poetry.utils.authenticator import Authenticator
from poetry.utils.helpers import get_cert
from poetry.utils.helpers import get_client_cert


if TYPE_CHECKING:
    from pathlib import Path

    from cleo.io import BufferedIO
    from cleo.io import ConsoleIO

    from poetry.poetry import Poetry

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
    def files(self) -> List["Path"]:
        return self._uploader.files

    def publish(
        self,
        repository_name: Optional[str],
        username: Optional[str],
        password: Optional[str],
        cert: Optional["Path"] = None,
        client_cert: Optional["Path"] = None,
        dry_run: bool = False,
    ) -> None:
        if not repository_name:
            url = "https://upload.pypi.org/legacy/"
            repository_name = "pypi"
        else:
            # Retrieving config information
            url = self._poetry.config.get(f"repositories.{repository_name}.url")
            if url is None:
                raise RuntimeError(f"Repository {repository_name} is not defined")
            is_publishable = self._poetry.config.get(
                f"repositories.{repository_name}.publish"
            )

            if is_publishable is False:
                self._io.write_line(
                    f"<error>{repository_name} is not a publishable repository. "
                    "Configure one using the poetry config command</error>"
                )
                raise RuntimeError(
                    f"{repository_name} is a source and cannot be published to"
                )

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
                        f"Found authentication information for {repository_name}."
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

        if repository_name == "pypi":
            repository_name = "PyPI"
        self._io.write_line(
            f"Publishing <c1>{self._package.pretty_name}</c1>"
            f" (<c2>{self._package.pretty_version}</c2>) to"
            f" <info>{repository_name}</info>"
        )

        self._uploader.upload(
            url,
            cert=cert or get_cert(self._poetry.config, repository_name),
            client_cert=resolved_client_cert,
            dry_run=dry_run,
        )
