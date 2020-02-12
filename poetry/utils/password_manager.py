import logging


logger = logging.getLogger(__name__)


class PasswordManagerError(Exception):

    pass


class KeyRingError(Exception):

    pass


class KeyRing:
    def __init__(self, namespace):
        self._namespace = namespace
        self._is_available = True

        self._check()

    def is_available(self):
        return self._is_available

    def get_password(self, name, username):
        if not self.is_available():
            return

        import keyring
        import keyring.errors

        name = self.get_entry_name(name)

        try:
            return keyring.get_password(name, username)
        except (RuntimeError, keyring.errors.KeyringError):
            raise KeyRingError(
                "Unable to retrieve the password for {} from the key ring".format(name)
            )

    def set_password(self, name, username, password):
        if not self.is_available():
            return

        import keyring
        import keyring.errors

        name = self.get_entry_name(name)

        try:
            keyring.set_password(name, username, password)
        except (RuntimeError, keyring.errors.KeyringError) as e:
            raise KeyRingError(
                "Unable to store the password for {} in the key ring: {}".format(
                    name, str(e)
                )
            )

    def delete_password(self, name, username):
        if not self.is_available():
            return

        import keyring
        import keyring.errors

        name = self.get_entry_name(name)

        try:
            keyring.delete_password(name, username)
        except (RuntimeError, keyring.errors.KeyringError):
            raise KeyRingError(
                "Unable to delete the password for {} from the key ring".format(name)
            )

    def get_entry_name(self, name):
        return "{}-{}".format(self._namespace, name)

    def _check(self):
        try:
            import keyring
        except Exception as e:
            logger.debug("An error occurred while importing keyring: {}".format(str(e)))
            self._is_available = False

            return

        backend = keyring.get_keyring()
        name = backend.name.split(" ")[0]
        if name == "fail":
            logger.debug("No suitable keyring backend found")
            self._is_available = False
        elif "plaintext" in backend.name.lower():
            logger.debug("Only a plaintext keyring backend is available. Not using it.")
            self._is_available = False
        elif name == "chainer":
            try:
                import keyring.backend

                backends = keyring.backend.get_all_keyring()

                self._is_available = any(
                    [
                        b.name.split(" ")[0] not in ["chainer", "fail"]
                        and "plaintext" not in b.name.lower()
                        for b in backends
                    ]
                )
            except Exception:
                self._is_available = False

        if not self._is_available:
            logger.warning("No suitable keyring backends were found")


class PasswordManager:
    def __init__(self, config):
        self._config = config
        self._keyring = None

    @property
    def keyring(self):
        if self._keyring is None:
            self._keyring = KeyRing("poetry-repository")
            if not self._keyring.is_available():
                logger.warning(
                    "Using a plaintext file to store and retrieve credentials"
                )

        return self._keyring

    def set_pypi_token(self, name, token):
        if not self.keyring.is_available():
            self._config.auth_config_source.add_property(
                "pypi-token.{}".format(name), token
            )
        else:
            self.keyring.set_password(name, "__token__", token)

    def get_pypi_token(self, name):
        if not self.keyring.is_available():
            return self._config.get("pypi-token.{}".format(name))

        return self.keyring.get_password(name, "__token__")

    def delete_pypi_token(self, name):
        if not self.keyring.is_available():
            return self._config.auth_config_source.remove_property(
                "pypi-token.{}".format(name)
            )

        self.keyring.delete_password(name, "__token__")

    def get_http_auth(self, name):
        auth = self._config.get("http-basic.{}".format(name))
        if not auth:
            username = self._config.get("http-basic.{}.username".format(name))
            password = self._config.get("http-basic.{}.password".format(name))
            if not username and not password:
                return None
        else:
            username, password = auth["username"], auth.get("password")
            if password is None:
                password = self.keyring.get_password(name, username)

        return {
            "username": username,
            "password": password,
        }

    def set_http_password(self, name, username, password):
        auth = {"username": username}

        if not self.keyring.is_available():
            auth["password"] = password
        else:
            self.keyring.set_password(name, username, password)

        self._config.auth_config_source.add_property("http-basic.{}".format(name), auth)

    def delete_http_password(self, name):
        auth = self.get_http_auth(name)
        if not auth or "username" not in auth:
            return

        try:
            self.keyring.delete_password(name, auth["username"])
        except KeyRingError:
            pass

        self._config.auth_config_source.remove_property("http-basic.{}".format(name))
