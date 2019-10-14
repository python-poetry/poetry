# Configuration

Poetry can be configured via the `config` command ([see more about its usage here](/docs/cli/#config))
or directly in the `config.toml` file that will be automatically be created when you first run that command.
This file can typically be found in one of the following directories:

- macOS:   `~/Library/Application Support/pypoetry`
- Windows: `C:\Users\<username>\AppData\Roaming\pypoetry`

For Unix, we follow the XDG spec and support `$XDG_CONFIG_HOME`.
That means, by default `~/.config/pypoetry`.

## Local configuration

Poetry also provides the ability to have settings that are specific to a project
by passing the `--local` option to the `config` command.

```bash
poetry config virtualenvs.create false --local
```

## Listing the current configuration

To list the current configuration you can use the `--list` option
of the `config` command:

```bash
poetry config --list
```

which will give you something similar to this:

```toml
cache-dir = "/path/to/cache/directory"
virtualenvs.create = true
virtualenvs.in-project = false
virtualenvs.path = "{cache-dir}/virtualenvs"  # /path/to/cache/directory/virtualenvs
```

## Displaying a single configuration setting

If you want to see the value of a specific setting, you can
give its name to the `config` command

```bash
poetry config virtualenvs.path
```

For a full list of the supported settings see [Available settings](#available-settings).

## Adding or updating a configuration setting

To change or otherwise add a new configuration setting, you can pass
a value after the setting's name:

```bash
poetry config virtualenvs.path /path/to/cache/directory/virtualenvs
```

For a full list of the supported settings see [Available settings](#available-settings).

## Removing a specific setting

If you want to remove a previously set setting, you can use the `--unset` option:

```bash
poetry config virtualenvs.path --unset
```

The setting will then retrieve its default value.

## Using environment variables

Sometimes, in particular when using Poetry with CI tools, it's easier
to use environment variables and not have to execute configuration commands.

Poetry supports this and any setting can be set by using environment variables.

The environment variables must be prefixed by `POETRY_` and are comprised of the uppercase
name of the setting and with dots and dashes replaced by underscore, here is an example:

```bash
export POETRY_VIRTUALENVS_PATH=/path/to/virtualenvs/directory
```

This also works for secret settings, like credentials:

```bash
export POETRY_HTTP_BASIC_MY_REPOSITORY_PASSWORD=secret
```


## Available settings

### `cache-dir`: string

The path to the cache directory used by Poetry.

Defaults to one of the following directories:

- macOS:   `~/Library/Caches/pypoetry`
- Windows: `C:\Users\<username>\AppData\Local\pypoetry\Cache`
- Unix:    `~/.cache/pypoetry/virtualenvs`

### `virtualenvs.create`: boolean

Create a new virtualenv if one doesn't already exist.
Defaults to `true`.

### `virtualenvs.in-project`: boolean

Create the virtualenv inside the project's root directory.
Defaults to `false`.

### `virtualenvs.path`: string

Directory where virtualenvs will be created.
Defaults to `{cache-dir}/virtualenvs` (`{cache-dir}\virtualenvs` on Windows).

### `repositories.<name>`: string

Set a new alternative repository. See [Repositories](/docs/repositories/) for more information.
