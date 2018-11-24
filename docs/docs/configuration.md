# Configuration

Poetry can be configured via the `config` command ([see more about its usage here](/docs/cli/#config))
or directly in the `config.toml` file that will be automatically be created when you first run that command.
This file can typically be found in one of the following directories:

- macOS:   `~/Library/Application Support/pypoetry`
- Windows: `C:\Users\<username>\AppData\Roaming\pypoetry`

For Unix, we follow the XDG spec and support `$XDG_CONFIG_HOME`.
That means, by default `~/.config/pypoetry`.

## Available settings

### `settings.virtualenvs.create`: boolean

Create a new virtualenv if one doesn't already exist.
Defaults to `true`.

### `settings.virtualenvs.in-project`: boolean

Create the virtualenv inside the project's root directory.
Defaults to `false`.

### `settings.virtualenvs.path`: string

Directory where virtualenvs will be created.
Defaults to one of the following directories:

- macOS:   `~/Library/Caches/pypoetry/virtualenvs`
- Windows: `C:\Users\<username>\AppData\Local\pypoetry\Cache/virtualenvs`
- Unix:    `~/.cache/pypoetry/virtualenvs`

### `repositories.<name>`: string

Set a new alternative repository. See [Repositories](/docs/repositories/) for more information.
