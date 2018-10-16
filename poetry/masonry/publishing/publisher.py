from poetry.locations import CONFIG_DIR
from poetry.utils._compat import Path
from poetry.utils.helpers import get_http_basic_auth
from poetry.utils.toml_file import TomlFile

from .uploader import Uploader


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

    def publish(self, repository_name, username, password):
        if repository_name:
            self._io.writeln(
                "Publishing <info>{}</info> (<comment>{}</comment>) "
                "to <fg=cyan>{}</>".format(
                    self._package.pretty_name,
                    self._package.pretty_version,
                    repository_name,
                )
            )
        else:
            self._io.writeln(
                "Publishing <info>{}</info> (<comment>{}</comment>) "
                "to <fg=cyan>PyPI</>".format(
                    self._package.pretty_name, self._package.pretty_version
                )
            )

        if not repository_name:
            url = "https://upload.pypi.org/legacy/"
            repository_name = "pypi"
        else:
            # Retrieving config information
            config_file = TomlFile(Path(CONFIG_DIR) / "config.toml")

            if not config_file.exists():
                raise RuntimeError(
                    "Config file does not exist. "
                    "Unable to get repository information"
                )

            config = config_file.read()

            if (
                "repositories" not in config
                or repository_name not in config["repositories"]
            ):
                raise RuntimeError(
                    "Repository {} is not defined".format(repository_name)
                )

            url = config["repositories"][repository_name]["url"]

        if not (username and password):
            auth = get_http_basic_auth(self._poetry.auth_config, repository_name)
            if auth:
                username = auth[0]
                password = auth[1]

        # Requesting missing credentials
        if not username:
            username = self._io.ask("Username:")

        if password is None:
            password = self._io.ask_hidden("Password:")

        # TODO: handle certificates

        self._uploader.auth(username, password)

        return self._uploader.upload(url)
