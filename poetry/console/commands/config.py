import json
import re

from .command import Command


TEMPLATE = """[settings]

[repositories]
"""

AUTH_TEMPLATE = """[http-basic]
"""


class ConfigCommand(Command):
    """
    Sets/Gets config options.

    config
        { key : Setting key. }
        { value?* : Setting value. }
        { --list : List configuration settings }
        { --unset : Unset configuration setting }
    """

    help = """This command allows you to edit the poetry config settings and repositories.

To add a repository:

    <comment>poetry config repositories.foo https://bar.com/simple/</comment>

To remove a repository (repo is a short alias for repositories):

    <comment>poetry config --unset repo.foo</comment>
"""

    def __init__(self):
        from poetry.config import Config

        super(ConfigCommand, self).__init__()

        self._config = Config.create("config.toml")
        self._auth_config = Config.create("auth.toml")

    @property
    def unique_config_values(self):
        from poetry.locations import CACHE_DIR
        from poetry.utils._compat import Path

        boolean_validator = lambda val: val in {"true", "false", "1", "0"}
        boolean_normalizer = lambda val: True if val in ["true", "1"] else False

        unique_config_values = {
            "settings.virtualenvs.create": (
                boolean_validator,
                boolean_normalizer,
                True,
            ),
            "settings.virtualenvs.in-project": (
                boolean_validator,
                boolean_normalizer,
                False,
            ),
            "settings.virtualenvs.path": (
                str,
                lambda val: str(Path(val).resolve()),
                str(Path(CACHE_DIR) / "virtualenvs"),
            ),
        }

        return unique_config_values

    def initialize(self, i, o):
        from poetry.utils._compat import decode

        super(ConfigCommand, self).initialize(i, o)

        # Create config file if it does not exist
        if not self._config.file.exists():
            self._config.file.parent.mkdir(parents=True, exist_ok=True)
            with self._config.file.open("w", encoding="utf-8") as f:
                f.write(decode(TEMPLATE))

        if not self._auth_config.file.exists():
            self._auth_config.file.parent.mkdir(parents=True, exist_ok=True)
            with self._auth_config.file.open("w", encoding="utf-8") as f:
                f.write(decode(AUTH_TEMPLATE))

    def handle(self):
        if self.option("list"):
            self._list_configuration(self._config.content)

            return 0

        setting_key = self.argument("key")
        if not setting_key:
            return 0

        if self.argument("value") and self.option("unset"):
            raise RuntimeError("You can not combine a setting value with --unset")

        # show the value if no value is provided
        if not self.argument("value") and not self.option("unset"):
            m = re.match("^repos?(?:itories)?(?:\.(.+))?", self.argument("key"))
            if m:
                if not m.group(1):
                    value = {}
                    if self._config.setting("repositories") is not None:
                        value = self._config.setting("repositories")
                else:
                    repo = self._config.setting("repositories.{}".format(m.group(1)))
                    if repo is None:
                        raise ValueError(
                            "There is no {} repository defined".format(m.group(1))
                        )

                    value = repo

                self.line(str(value))
            else:
                values = self.unique_config_values
                if setting_key not in values:
                    raise ValueError("There is no {} setting.".format(setting_key))

                values = self._get_setting(
                    self._config.content, setting_key, default=values[setting_key][-1]
                )

                for value in values:
                    self.line(value[1])

            return 0

        values = self.argument("value")

        unique_config_values = self.unique_config_values
        if setting_key in unique_config_values:
            if self.option("unset"):
                return self._remove_single_value(setting_key)

            return self._handle_single_value(
                setting_key, unique_config_values[setting_key], values
            )

        # handle repositories
        m = re.match("^repos?(?:itories)?(?:\.(.+))?", self.argument("key"))
        if m:
            if not m.group(1):
                raise ValueError("You cannot remove the [repositories] section")

            if self.option("unset"):
                repo = self._config.setting("repositories.{}".format(m.group(1)))
                if repo is None:
                    raise ValueError(
                        "There is no {} repository defined".format(m.group(1))
                    )

                self._config.remove_property("repositories.{}".format(m.group(1)))

                return 0

            if len(values) == 1:
                url = values[0]

                self._config.add_property("repositories.{}.url".format(m.group(1)), url)

                return 0

            raise ValueError(
                "You must pass the url. "
                "Example: poetry config repositories.foo https://bar.com"
            )

        # handle auth
        m = re.match("^(http-basic)\.(.+)", self.argument("key"))
        if m:
            if self.option("unset"):
                if not self._auth_config.setting(
                    "{}.{}".format(m.group(1), m.group(2))
                ):
                    raise ValueError(
                        "There is no {} {} defined".format(m.group(2), m.group(1))
                    )

                self._auth_config.remove_property(
                    "{}.{}".format(m.group(1), m.group(2))
                )

                return 0

            if m.group(1) == "http-basic":
                if len(values) == 1:
                    username = values[0]
                    # Only username, so we prompt for password
                    password = self.secret("Password:")
                elif len(values) != 2:
                    raise ValueError(
                        "Expected one or two arguments "
                        "(username, password), got {}".format(len(values))
                    )
                else:
                    username = values[0]
                    password = values[1]

                self._auth_config.add_property(
                    "{}.{}".format(m.group(1), m.group(2)),
                    {"username": username, "password": password},
                )

            return 0

        raise ValueError("Setting {} does not exist".format(self.argument("key")))

    def _handle_single_value(self, key, callbacks, values):
        validator, normalizer, _ = callbacks

        if len(values) > 1:
            raise RuntimeError("You can only pass one value.")

        value = values[0]
        if not validator(value):
            raise RuntimeError('"{}" is an invalid value for {}'.format(value, key))

        self._config.add_property(key, normalizer(value))

        return 0

    def _remove_single_value(self, key):
        self._config.remove_property(key)

        return 0

    def _list_configuration(self, contents):
        if "settings" not in contents:
            settings = {}
        else:
            settings = contents["settings"]
        for setting_key, value in sorted(self.unique_config_values.items()):
            self._list_setting(
                settings,
                setting_key.replace("settings.", ""),
                "settings.",
                default=value[-1],
            )

        repositories = contents.get("repositories")
        if not repositories:
            self.line("<comment>repositories</comment> = <info>{}</info>")
        else:
            self._list_setting(repositories, k="repositories.")

    def _list_setting(self, contents, setting=None, k=None, default=None):
        values = self._get_setting(contents, setting, k, default)

        for value in values:
            self.line(
                "<comment>{}</comment> = <info>{}</info>".format(value[0], value[1])
            )

    def _get_setting(self, contents, setting=None, k=None, default=None):
        orig_k = k

        if setting and setting.split(".")[0] not in contents:
            value = json.dumps(default)

            return [((k or "") + setting, value)]
        else:
            values = []
            for key, value in contents.items():
                if k is None and key not in ["config", "repositories", "settings"]:
                    continue

                if setting and key != setting.split(".")[0]:
                    continue

                if isinstance(value, dict) or key == "repositories" and k is None:
                    if k is None:
                        k = ""

                    k += re.sub("^config\.", "", key + ".")
                    if setting and len(setting) > 1:
                        setting = ".".join(setting.split(".")[1:])

                    values += self._get_setting(
                        value, k=k, setting=setting, default=default
                    )
                    k = orig_k

                    continue

                if isinstance(value, list):
                    value = [
                        json.dumps(val) if isinstance(val, list) else val
                        for val in value
                    ]

                    value = "[{}]".format(", ".join(value))

                value = json.dumps(value)

                values.append(((k or "") + key, value))

            return values

    def _get_formatted_value(self, value):
        if isinstance(value, list):
            value = [json.dumps(val) if isinstance(val, list) else val for val in value]

            value = "[{}]".format(", ".join(value))

        return json.dumps(value)
