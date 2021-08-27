---
title: "Configuration"
draft: false
type: docs
layout: single

menu:
  docs:
    weight: 40
---

# Configuration

Poetry can be configured via the `config` command ([see more about its usage here]({{< relref "cli#config" >}} "config command documentation"))
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
virtualenvs.in-project = null
virtualenvs.options.always-copy = true
virtualenvs.options.system-site-packages = false
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

### `cache-dir`

**Type**: string

The path to the cache directory used by Poetry.

Defaults to one of the following directories:

- macOS:   `~/Library/Caches/pypoetry`
- Windows: `C:\Users\<username>\AppData\Local\pypoetry\Cache`
- Unix:    `~/.cache/pypoetry`

### `installer.parallel`

**Type**: boolean

Use parallel execution when using the new (`>=1.1.0`) installer.
Defaults to `true`.

<<<<<<< HEAD
### `installer.max-workers`

**Type**: int

Set the maximum number of workers while using the parallel installer. Defaults to `number_of_cores + 4`.
The `number_of_cores` is determined by `os.cpu_count()`.
If this raises a `NotImplentedError` exception `number_of_cores` is assumed to be 1.

If this configuration parameter is set to a value greater than `number_of_cores + 4`,
the number of maximum workers is still limited at `number_of_cores + 4`.

{{% note %}}
This configuration will be ignored when `installer.parallel` is set to false.
=======
{{% note %}}
This configuration will be ignored, and parallel execution disabled when running
Python 2.7 under Windows.
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
{{% /note %}}

### `virtualenvs.create`

**Type**: boolean

Create a new virtual environment if one doesn't already exist.
Defaults to `true`.

If set to `false`, poetry will install dependencies into the current python environment.

{{% note %}}
When setting this configuration to `false`, the Python environment used must have `pip`
installed and available.
{{% /note %}}

### `virtualenvs.in-project`

**Type**: boolean

Create the virtualenv inside the project's root directory.
Defaults to `None`.

If set to `true`, the virtualenv will be created and expected in a folder named
`.venv` within the root directory of the project.

If not set explicitly (default), `poetry` will use the virtualenv from the `.venv`
directory when one is available. If set to `false`, `poetry` will ignore any
existing `.venv` directory.

### `virtualenvs.path`

**Type**: string

Directory where virtual environments will be created.
Defaults to `{cache-dir}/virtualenvs` (`{cache-dir}\virtualenvs` on Windows).

### `virtualenvs.options.always-copy`

**Type**: boolean

If set to `true` the `--always-copy` parameter is passed to `virtualenv` on creation of the venv. Thus all needed files are copied into the venv instead of symlinked.
Defaults to `false`.

### `virtualenvs.options.system-site-packages`

**Type**: boolean

Give the virtual environment access to the system site-packages directory.
Applies on virtualenv creation.
Defaults to `false`.

### `repositories.<name>`

**Type**: string

Set a new alternative repository. See [Repositories]({{< relref "repositories" >}}) for more information.
