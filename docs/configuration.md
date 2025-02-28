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
or directly in the `config.toml` file that will be automatically created when you first run that command.
This file can typically be found in one of the following directories:

- macOS:   `~/Library/Application Support/pypoetry`
- Windows: `%APPDATA%\pypoetry`

For Unix, we follow the XDG spec and support `$XDG_CONFIG_HOME`.
That means, by default `~/.config/pypoetry`.

## Local configuration

Poetry also provides the ability to have settings that are specific to a project
by passing the `--local` option to the `config` command.

```bash
poetry config virtualenvs.create false --local
```

{{% note %}}
Your local configuration of Poetry application is stored in the `poetry.toml` file,
which is separate from `pyproject.toml`.
{{% /note %}}

{{% warning %}}
Be mindful about checking in this file into your repository since it may contain user-specific or sensitive information.
{{% /note %}}

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
virtualenvs.options.no-pip = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = "{cache-dir}/virtualenvs"  # /path/to/cache/directory/virtualenvs
virtualenvs.prompt = "{project_name}-py{python_version}"
virtualenvs.use-poetry-python = false
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

## Migrate outdated configs

If Poetry renames or remove config options it might be necessary to migrate explicit set options. This is possible
by running:

```bash
poetry config --migrate
```

If you need to migrate a local config run:

```bash
poetry config --migrate --local
```

## Default Directories

Poetry uses the following default directories:

### Config Directory

- Linux: `$XDG_CONFIG_HOME/pypoetry` or `~/.config/pypoetry`
- Windows: `%APPDATA%\pypoetry`
- macOS: `~/Library/Application Support/pypoetry`

You can override the config directory by setting the `POETRY_CONFIG_DIR` environment variable.

### Data Directory

- Linux: `$XDG_DATA_HOME/pypoetry` or `~/.local/share/pypoetry`
- Windows: `%APPDATA%\pypoetry`
- macOS: `~/Library/Application Support/pypoetry`

You can override the data directory by setting the `POETRY_DATA_DIR` or `POETRY_HOME` environment variables. If `POETRY_HOME` is set, it will be given higher priority.

### Cache Directory

- Linux: `$XDG_CACHE_HOME/pypoetry` or `~/.cache/pypoetry`
- Windows: `%LOCALAPPDATA%\pypoetry`
- macOS: `~/Library/Caches/pypoetry`

You can override the cache directory by setting the `POETRY_CACHE_DIR` environment variable.

## Available settings

### `cache-dir`

**Type**: `string`

**Environment Variable**: `POETRY_CACHE_DIR`

The path to the cache directory used by Poetry.

Defaults to one of the following directories:

- macOS:   `~/Library/Caches/pypoetry`
- Windows: `C:\Users\<username>\AppData\Local\pypoetry\Cache`
- Unix:    `~/.cache/pypoetry`

### `data-dir`

**Type**: `string`

**Environment Variable**: `POETRY_DATA_DIR`

The path to the data directory used by Poetry.

- Linux: `$XDG_DATA_HOME/pypoetry` or `~/.local/share/pypoetry`
- Windows: `%APPDATA%\pypoetry`
- macOS: `~/Library/Application Support/pypoetry`

You can override the data directory by setting the `POETRY_DATA_DIR` or `POETRY_HOME` environment variables. If
`POETRY_HOME` is set, it will be given higher priority.

### `installer.max-workers`

**Type**: `int`

**Default**: `number_of_cores + 4`

**Environment Variable**: `POETRY_INSTALLER_MAX_WORKERS`

*Introduced in 1.2.0*

Set the maximum number of workers while using the parallel installer.
The `number_of_cores` is determined by `os.cpu_count()`.
If this raises a `NotImplementedError` exception, `number_of_cores` is assumed to be 1.

If this configuration parameter is set to a value greater than `number_of_cores + 4`,
the number of maximum workers is still limited at `number_of_cores + 4`.

{{% note %}}
This configuration is ignored when `installer.parallel` is set to `false`.
{{% /note %}}

### `installer.no-binary`

**Type**: `string | boolean`

**Default**: `false`

**Environment Variable**: `POETRY_INSTALLER_NO_BINARY`

*Introduced in 1.2.0*

When set, this configuration allows users to disallow the use of binary distribution format for all, none or specific packages.

| Configuration          | Description                                                |
|------------------------|------------------------------------------------------------|
| `:all:` or `true`      | Disallow binary distributions for all packages.            |
| `:none:` or `false`    | Allow binary distributions for all packages.               |
| `package[,package,..]` | Disallow binary distributions for specified packages only. |

{{% note %}}
As with all configurations described here, this is a user specific configuration. This means that this
is not taken into consideration when a lockfile is generated or dependencies are resolved. This is
applied only when selecting which distribution for dependency should be installed into a Poetry managed
environment.
{{% /note %}}

{{% note %}}
For project specific usage, it is recommended that this be configured with the `--local`.

```bash
poetry config --local installer.no-binary :all:
```
{{% /note %}}

{{% note %}}
For CI or container environments using [environment variable](#using-environment-variables)
to configure this might be useful.

```bash
export POETRY_INSTALLER_NO_BINARY=:all:
```
{{% /note %}}

{{% warning %}}
Unless this is required system-wide, if configured globally, you could encounter slower install times
across all your projects if incorrectly set.
{{% /warning %}}

### `installer.only-binary`

**Type**: `string | boolean`

**Default**: `false`

**Environment Variable**: `POETRY_INSTALLER_ONLY_BINARY`

*Introduced in 2.0.0*

When set, this configuration allows users to enforce the use of binary distribution format for all, none or
specific packages.

{{% note %}}
Please refer to [`installer.no-binary`]({{< relref "configuration#installerno-binary" >}}) for information on allowed
values, usage instructions and warnings.
{{% /note %}}

### `installer.parallel`

**Type**: `boolean`

**Default**: `true`

**Environment Variable**: `POETRY_INSTALLER_PARALLEL`

*Introduced in 1.1.4*

Use parallel execution when using the new (`>=1.1.0`) installer.

### `installer.build-config-settings.<package-name>`

**Type**: `Serialised JSON with string or list of string properties`

**Default**: `None`

**Environment Variable**: `POETRY_INSTALLER_BUILD_CONFIG_SETTINGS_<package-name>`

*Introduced in 2.1.0*

{{% warning %}}
This is an **experimental** configuration and can be subject to changes in upcoming releases until it is considered
stable.
{{% /warning %}}

Configure [PEP 517 config settings](https://peps.python.org/pep-0517/#config-settings) to be passed to a package's
build backend if it has to be built from a directory or vcs source; or a source distribution during installation.

This is only used when a compatible binary distribution (wheel) is not available for a package. This can be used along
with [`installer.no-binary`]({{< relref "configuration#installerno-binary" >}}) option to force a build with these
configurations when a dependency of your project with the specified name is being installed.

{{% note %}}
Poetry does not offer a similar option in the `pyproject.toml` file as these are, in majority of cases, not universal
and vary depending on the target installation environment.

If you want to use a project specific configuration it is recommended that this configuration be set locally, in your
project's `poetry.toml` file.

```bash
poetry config --local installer.build-config-settings.grpcio \
  '{"CC": "gcc", "--global-option": ["--some-global-option"], "--build-option": ["--build-option1", "--build-option2"]}'
```

If you want to modify a single key, you can do, by setting the same key again.

```bash
poetry config --local installer.build-config-settings.grpcio \
  '{"CC": "g++"}'
```

{{% /note %}}

### `requests.max-retries`

**Type**: `int`

**Default**: `0`

**Environment Variable**: `POETRY_REQUESTS_MAX_RETRIES`

*Introduced in 2.0.0*

Set the maximum number of retries in an unstable network.
This setting has no effect if the server does not support HTTP range requests.

### `installer.re-resolve`

**Type**: `boolean`

**Default**: `true`

**Environment Variable**: `POETRY_INSTALLER_RE_RESOLVE`

*Introduced in 2.0.0*

If the config option is _not_ set and the lock file is at least version 2.1
(created by Poetry 2.0 or above), the installer will not re-resolve dependencies
but evaluate the locked markers to decide which of the locked dependencies have to
be installed into the target environment.

### `python.installation-dir`

**Type**: `string`

**Default**: `{data-dir}/python`

**Environment Variable**: `POETRY_PYTHON_INSTALLATION_DIR`

*Introduced in 2.1.0*

The directory in which Poetry managed Python versions are installed to.

### `solver.lazy-wheel`

**Type**: `boolean`

**Default**: `true`

**Environment Variable**: `POETRY_SOLVER_LAZY_WHEEL`

*Introduced in 1.8.0*

Do not download entire wheels to extract metadata but use
[HTTP range requests](https://developer.mozilla.org/en-US/docs/Web/HTTP/Range_requests)
to only download the METADATA files of wheels.
Especially with slow network connections this setting can speed up dependency resolution significantly.
If the cache has already been filled or the server does not support HTTP range requests,
this setting makes no difference.

### `system-git-client`

**Type**: `boolean`

**Default**: `false`

**Environment Variable**: `POETRY_SYSTEM_GIT_CLIENT`

*Renamed to `system-git-client` in 2.0.0*

*Introduced in 1.2.0 as `experimental.system-git-client`*

Use system git client backend for git related tasks.

Poetry uses `dulwich` by default for git related tasks to not rely on the availability of a git client.

If you encounter any problems with it, set to `true` to use the system git backend.

### `virtualenvs.create`

**Type**: `boolean`

**Default**: `true`

**Environment Variable**: `POETRY_VIRTUALENVS_CREATE`

Create a new virtual environment if one doesn't already exist.

If set to `false`, Poetry will not create a new virtual environment. If it detects an already enabled virtual
environment or an existing one in `{cache-dir}/virtualenvs` or `{project-dir}/.venv` it will
install dependencies into them, otherwise it will install dependencies into the systems python environment.

{{% note %}}
If Poetry detects it's running within an activated virtual environment, it will never create a new virtual environment,
regardless of the value set for `virtualenvs.create`.
{{% /note %}}

{{% note %}}
Be aware that installing dependencies into the system environment likely upgrade or uninstall existing packages and thus
break other applications. Installing additional Python packages after installing the project might break the Poetry
project in return.

This is why it is recommended to always create a virtual environment. This is also true in Docker containers, as they
might contain additional Python packages as well.
{{% /note %}}

### `virtualenvs.in-project`

**Type**: `boolean`

**Default**: `None`

**Environment Variable**: `POETRY_VIRTUALENVS_IN_PROJECT`

Create the virtualenv inside the project's root directory.

If not set explicitly, `poetry` by default will create a virtual environment under
`{cache-dir}/virtualenvs` or use the `{project-dir}/.venv` directory if one already exists.

If set to `true`, the virtualenv will be created and expected in a folder named
`.venv` within the root directory of the project.

{{% note %}}
If a virtual environment has already been created for the project under `{cache-dir}/virtualenvs`, setting this variable to `true` will not cause `poetry` to create or use a local virtual environment.

In order for this setting to take effect for a project already in that state, you must delete the virtual environment folder located in `{cache-dir}/virtualenvs`.

You can find out where the current project's virtual environment (if there is one) is stored
with the command `poetry env info --path`.
{{% /note %}}

If set to `false`, `poetry` will ignore any existing `.venv` directory.

### `virtualenvs.options.always-copy`

**Type**: `boolean`

**Default**: `false`

**Environment Variable**: `POETRY_VIRTUALENVS_OPTIONS_ALWAYS_COPY`

*Introduced in 1.2.0*

If set to `true` the `--always-copy` parameter is passed to `virtualenv` on creation of the virtual environment, so that
all needed files are copied into it instead of symlinked.

### `virtualenvs.options.no-pip`

**Type**: `boolean`

**Default**: `false`

**Environment Variable**: `POETRY_VIRTUALENVS_OPTIONS_NO_PIP`

*Introduced in 1.2.0*

If set to `true` the `--no-pip` parameter is passed to `virtualenv` on creation of the virtual environment. This means
when a new virtual environment is created, `pip` will not be installed in the environment.

{{% note %}}
Poetry, for its internal operations, uses the `pip` wheel embedded in the `virtualenv` package installed as a dependency
in Poetry's runtime environment. If a user runs `poetry run pip` when this option is set to `true`, the `pip` the
embedded instance of `pip` is used.

You can safely set this to `true`, if you desire a virtual environment with no additional packages.
This is desirable for production environments.
{{% /note %}}

### `virtualenvs.options.system-site-packages`

**Type**: `boolean`

**Default**: `false`

**Environment Variable**: `POETRY_VIRTUALENVS_OPTIONS_SYSTEM_SITE_PACKAGES`

Give the virtual environment access to the system site-packages directory.
Applies on virtualenv creation.

### `virtualenvs.path`

**Type**: `string`

**Default**: `{cache-dir}/virtualenvs`

**Environment Variable**: `POETRY_VIRTUALENVS_PATH`

Directory where virtual environments will be created.

{{% note %}}
This setting controls the global virtual environment storage path. It most likely will not be useful at the local level. To store virtual environments in the project root, see `virtualenvs.in-project`.
{{% /note %}}

### `virtualenvs.prompt`

**Type**: `string`

**Default**: `{project_name}-py{python_version}`

**Environment Variable**: `POETRY_VIRTUALENVS_PROMPT`

*Introduced in 1.2.0*

Format string defining the prompt to be displayed when the virtual environment is activated.
The variables `project_name` and `python_version` are available for formatting.

### `virtualenvs.use-poetry-python`

**Type**: `boolean`

**Default**: `false`

**Environment Variable**: `POETRY_VIRTUALENVS_USE_POETRY_PYTHON`

*Introduced in 2.0.0*

By default, Poetry will use the activated Python version to create a new virtual environment.
If set to `true`, the Python version used during Poetry installation is used.

### `repositories.<name>.url`

**Type**: `string`

**Environment Variable**: `POETRY_REPOSITORIES_<NAME>_URL`

Set the repository URL for `<name>`.

See [Publishable Repositories]({{< relref "repositories#publishable-repositories" >}}) for more information.

### `http-basic.<name>.[username|password]`

**Type**: `string`

**Environment Variables**: `POETRY_HTTP_BASIC_<NAME>_USERNAME`, `POETRY_HTTP_BASIC_<NAME>_PASSWORD`

Set repository credentials (`username` and `password`) for `<name>`.
See [Repositories - Configuring credentials]({{< relref "repositories#configuring-credentials" >}})
for more information.

### `pypi-token.<name>`

**Type**: `string`

**Environment Variable**: `POETRY_PYPI_TOKEN_<NAME>`

Set repository credentials (using an API token) for `<name>`.
See [Repositories - Configuring credentials]({{< relref "repositories#configuring-credentials" >}})
for more information.

### `certificates.<name>.cert`

**Type**: `string | boolean`

**Environment Variable**: `POETRY_CERTIFICATES_<NAME>_CERT`

Set custom certificate authority for repository `<name>`.
See [Repositories - Configuring credentials - Custom certificate authority]({{< relref "repositories#custom-certificate-authority-and-mutual-tls-authentication" >}})
for more information.

This configuration can be set to `false`, if TLS certificate verification should be skipped for this
repository.

### `certificates.<name>.client-cert`

**Type**: `string`

**Environment Variable**: `POETRY_CERTIFICATES_<NAME>_CLIENT_CERT`

Set client certificate for repository `<name>`.
See [Repositories - Configuring credentials - Custom certificate authority]({{< relref "repositories#custom-certificate-authority-and-mutual-tls-authentication" >}})
for more information.

### `keyring.enabled`

**Type**: `boolean`

**Default**: `true`

**Environment Variable**: `POETRY_KEYRING_ENABLED`

Enable the system keyring for storing credentials.
See [Repositories - Configuring credentials]({{< relref "repositories#configuring-credentials" >}})
for more information.
