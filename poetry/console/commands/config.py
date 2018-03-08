import json
import re

from pathlib import Path

from poetry.locations import CONFIG_DIR
from poetry.toml import loads

from .command import Command


TEMPLATE = """[repositories]
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

        self._config_file = None
        self._config = {}

        self._auth_config_file = None
        self._auth_config = {}

    def initialize(self, i, o):
        super().initialize(i, o)

        # Create config file if it does not exist
        self._config_file = Path(CONFIG_DIR) / 'config.toml'
        self._auth_config_file = Path(CONFIG_DIR) / 'auth.toml'

        if not self._config_file.exists():
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            self._config_file.write_text(TEMPLATE)
        if not self._auth_config_file.exists():

            self._auth_config_file.parent.mkdir(parents=True, exist_ok=True)
            self._auth_config_file.write_text(AUTH_TEMPLATE)

        with self._config_file.open() as f:
            self._config = loads(f.read())

        with self._auth_config_file.open() as f:
            self._auth_config = loads(f.read())

    def handle(self):
        if self.option('list'):
            self._list_configuration(self._config)

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
                    if 'repositories' in self._config:
                        value = self._config['repositories']
                else:
                    if m.group(1) not in self._config['repositories']:
                        raise ValueError(
                            f'There is not {m.group(1)} repository defined'
                        )

                    value = self._config['repositories'][m.group(1)]

                self.line(str(value))

            return 0

        values = self.argument('value')

        # handle repositories
        m = re.match('^repos?(?:itories)?(?:\.(.+))?', self.argument('key'))
        if m:
            if not m.group(1):
                raise ValueError('You cannot remove the [repositories] section')

            if self.option('unset'):
                if m.group(1) not in self._config['repositories']:
                    raise ValueError(f'There is not {m.group(1)} repository defined')

                del self._config[m.group(1)]

                self._config_file.write_text(self._config.dumps())

                return 0

            if len(values) == 1:
                url = values[0]

                if m.group(1) in self._config['repositories']:
                    self._config['repositories'][m.group(1)]['url'] = url
                else:
                    self._config['repositories'][m.group(1)] = {
                        'url': url
                    }

                self._config_file.write_text(self._config.dumps())

                return 0

            raise ValueError(
                'You must pass the url. '
                'Example: poetry config repositories.foo https://bar.com'
            )

        # handle auth
        m = re.match('^(http-basic)\.(.+)', self.argument('key'))
        if m:
            if self.option('unset'):
                if m.group(2) not in self._auth_config[m.group(1)]:
                    raise ValueError(
                        f'There is no {m.group(2)} {m.group(1)} defined'
                    )

                del self._auth_config[m.group(1)][m.group(2)]

                self._auth_config_file.write_text(self._auth_config.dumps())

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

                self._auth_config[m.group(1)][m.group(2)] = {
                    'username': username,
                    'password': password
                }

            self._auth_config_file.write_text(self._auth_config.dumps())

            return 0

        raise ValueError(f'Setting {self.argument("key")} does not exist')

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
