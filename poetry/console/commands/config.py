import json
import re

from poetry.config import Config

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

    help = """This command allows you to edit the poetry config settings and repositories..

To add a repository:

    <comment>poetry repositories.foo https://bar.com/simple/</comment>

To remove a repository (repo is a short alias for repositories):

    <comment>poetry --unset repo.foo</comment>
"""

    def __init__(self):
        super().__init__()

        self._config = Config.create('config.toml')
        self._auth_config = Config.create('auth.toml')

    def initialize(self, i, o):
        super().initialize(i, o)

        # Create config file if it does not exist
        if not self._config.file.exists():
            self._config.file.parent.mkdir(parents=True, exist_ok=True)
            self._config.file.write_text(TEMPLATE)

        if not self._auth_config.file.exists():
            self._auth_config.file.parent.mkdir(parents=True, exist_ok=True)
            self._auth_config.file.write_text(AUTH_TEMPLATE)

    def handle(self):
        if self.option('list'):
            self._list_configuration(self._config.raw_content)

            return 0

        setting_key = self.argument('key')
        if not setting_key:
            return 0

        if self.argument('value') and self.option('unset'):
            raise RuntimeError('You can not combine a setting value with --unset')

        # show the value if no value is provided
        if not self.argument('value') and not self.option('unset'):
            m = re.match('^repos?(?:itories)?(?:\.(.+))?', self.argument('key'))
            if m:
                if not m.group(1):
                    value = {}
                    if self._config.setting('repositories') is not None:
                        value = self._config.setting('repositories')
                else:
                    repo = self._config.setting(f'repositories.{m.group(1)}')
                    if repo is None:
                        raise ValueError(
                            f'There is no {m.group(1)} repository defined'
                        )

                    value = repo

                self.line(str(value))

            return 0

        values = self.argument('value')

        boolean_validator = lambda val: val in {'true', 'false', '1', '0'}
        boolean_normalizer = lambda val: True if val in ['true', '1'] else False

        unique_config_values = {
            'settings.virtualenvs.create': (boolean_validator, boolean_normalizer)
        }

        if setting_key in unique_config_values:
            if self.option('unset'):
                return self._remove_single_value(setting_key)

            return self._handle_single_value(
                setting_key,
                unique_config_values[setting_key],
                values
            )

        # handle repositories
        m = re.match('^repos?(?:itories)?(?:\.(.+))?', self.argument('key'))
        if m:
            if not m.group(1):
                raise ValueError('You cannot remove the [repositories] section')

            if self.option('unset'):
                repo = self._config.setting(f'repositories.{m.group(1)}')
                if repo is None:
                    raise ValueError(f'There is no {m.group(1)} repository defined')

                self._config.remove_property(f'repositories.{m.group(1)}')

                return 0

            if len(values) == 1:
                url = values[0]

                self._config.add_property(f'repositories.{m.group(1)}.url', url)

                return 0

            raise ValueError(
                'You must pass the url. '
                'Example: poetry config repositories.foo https://bar.com'
            )

        # handle auth
        m = re.match('^(http-basic)\.(.+)', self.argument('key'))
        if m:
            if self.option('unset'):
                if not self._auth_config.setting(f'{m.group(1)}.{m.group(2)}'):
                    raise ValueError(
                        f'There is no {m.group(2)} {m.group(1)} defined'
                    )

                self._auth_config.remove_property(f'{m.group(1)}.{m.group(2)}')

                return 0

            if m.group(1) == 'http-basic':
                if len(values) == 1:
                    username = values[0]
                    # Only username, so we prompt for password
                    password = self.secret('Password:')
                elif len(values) != 2:
                    raise ValueError(f'Expected one or two arguments '
                                     f'(username, password), got {len(values)}')
                else:
                    username = values[0]
                    password = values[1]

                self._auth_config.add_property(
                    f'{m.group(1)}.{m.group(2)}', {
                        'username': username,
                        'password': password
                    }
                )

            return 0

        raise ValueError(f'Setting {self.argument("key")} does not exist')

    def _handle_single_value(self, key, callbacks, values):
        validator, normalizer = callbacks

        if len(values) > 1:
            raise RuntimeError('You can only pass one value.')

        value = values[0]
        if not validator(value):
            raise RuntimeError(
                f'"{value}" is an invalid value for {key}'
            )

        self._config.add_property(key, normalizer(value))

        return 0

    def _remove_single_value(self, key):
        self._config.remove_property(key)

        return 0

    def _list_configuration(self, contents, k=None):
        orig_k = k

        for key, value in contents.items():
            if k is None and key not in ['config', 'repositories']:
                continue

            if isinstance(value, dict) or key == 'repositories' and k is None:
                if k is None:
                    k = ''

                k += re.sub('^config\.', '', key + '.')
                self._list_configuration(value, k=k)
                k = orig_k

                continue

            if isinstance(value, list):
                value = [
                    json.dumps(val) if isinstance(val, list) else val
                    for val in value
                ]

                value = f'[{", ".join(value)}]'

            value = json.dumps(value)

            self.line(f'[<comment>{(k or "") + key}</comment>] <info>{value}</info>')
