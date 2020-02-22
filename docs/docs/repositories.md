# Repositories

## Using the PyPI repository

By default, Poetry is configured to use the [PyPI](https://pypi.org) repository,
for package installation and publishing.

So, when you add dependencies to your project, Poetry will assume they are available
on PyPI.

This represents most cases and will likely be enough for most users.


## Using a private repository

However, at times, you may need to keep your package private while still being
able to share it with your teammates. In this case, you will need to use a private
repository.

### Adding a repository

#### Adding a repository globally

You can add new repository either globally or for a specific project.
The easiest way to add a new repository is with the `config` command:

```bash
poetry config repositories.foo https://foo.bar/simple/
```

But you can also edit the `config.toml` directly:
```toml
[repositories]
[repositories.foo]
name = "foo"
url = "https://foo.bar/simple/"
```

With both options you will register new repository with name `foo` and set the url for repository `foo` to `https://foo.bar/simple/`.
From now on, Poetry will also look for packages in your private repository.
Any custom repository will have precedence over [PyPI](https://pypi.org).

You can add multiple repositories (but each repository **must** have a unique name):
```bash
poetry config repositories.foo https://foo.bar/simple/
poetry config repositories.bar https://bar.bar/simple/
```

But you can also edit the `config.toml` directly:
```toml
[repositories]
[repositories.foo]
name = "foo"
url = "https://foo.bar/simple/"

[repositories.bar]
name = "bar"
url = "https://foo.bar/simple/"
```

#### Adding a repository only for specific project

To add new repository only for a specific project you have to edit your `pyproject.toml` file and add:
```toml
[[tool.poetry.source]]
name = "foo"
url = "https://foo.bar/simple/"
```

From now on, Poetry will also look for packages in your private repository for this specific project.
Any custom repository project specific repository will also have precedence over [PyPI](https://pypi.org).

You can add multiple repositories (but each repository **must** have a unique name):
```toml
[[tool.poetry.source]]
name = "foo"
url = "https://foo.bar/simple/"

[[tool.poetry.source]]
name = "bar"
url = "https://bar.bar/simple/"
```

#### How global and project specific repositories work together

You can have repository with the same name in both global and project specific configs.
Settings from project specific configs for repository with the same name will override settings from global config ([except `global` flag](#disabling-the-pypi-repository)).

### Configuring credentials

If you want to store your credentials for a specific repository, you can do so easily:

```bash
poetry config http-basic.foo username password
```

If you do not specify the password you will be prompted to write it.

!!!note

    To publish to PyPI, you can set your credentials for the repository named `pypi`.

    Note that it is recommended to use [API tokens](https://pypi.org/help/#apitoken)
    when uploading packages to PyPI.
    Once you have created a new token, you can tell Poetry to use it:

    ```bash
    poetry config pypi-token.pypi my-token
    ```

    If you still want to use you username and password, you can do so with the following
    call to `config`.

    ```bash
    poetry config http-basic.pypi username password
    ```

You can also specify the username and password when using the `publish` command
with the `--username` and `--password` options.

If a system keyring is available and supported, the password is stored to and retrieved from the keyring. In the above example, the credential will be stored using the name `poetry-repository-pypi`. If access to keyring fails or is unsupported, this will fall back to writing the password to the `auth.toml` file along with the username.

Keyring support is enabled using the [keyring library](https://pypi.org/project/keyring/). For more information on supported backends refer to the [library documentation](https://keyring.readthedocs.io/en/latest/?badge=latest).

Alternatively, you can use environment variables to provide the credentials:

```bash
export POETRY_PYPI_TOKEN_PYPI=my-token
export POETRY_HTTP_BASIC_PYPI_USERNAME=username
export POETRY_HTTP_BASIC_PYPI_PASSWORD=password
```

See [Using environment variables](/docs/configuration/#using-environment-variables) for more information
on how to configure Poetry with environment variables.

#### Custom certificate authority and mutual TLS authentication
Poetry supports repositories that are secured by a custom certificate authority as well as those that require
certificate-based client authentication.  The following will configure the "foo" repository to validate the repository's
certificate using a custom certificate authority and use a client certificate (note that these config variables do not
both need to be set):
```bash
poetry config certificates.foo.cert /path/to/ca.pem
poetry config certificates.foo.client-cert /path/to/client.pem
```

### Install dependencies from a private repository

Once you added your private repository to the global or project specific config - Poetry will also look for packages in your private repository.

!!!note

    Any custom repository will have precedence over PyPI.

    If you still want PyPI to be your primary source for your packages
    you can declare custom repositories as secondary.

    **pyproject.toml**
    ```toml
    [[tool.poetry.source]]
    name = "foo"
    url = "https://foo.bar/simple/"
    secondary = true
    ```

    **CLI**
    ```bash
    poetry config repositories.foo.secondary true
    ```

    **config.toml**
    ```toml
    [repositories.foo]
    name = "foo"
    url = "https://foo.bar/simple/"
    secondary = true
    ```

If your private repository requires HTTP Basic Auth be sure to add the username and
password to your `http-basic` configuration using the example above (be sure to use the
same name that is in the `tool.poetry.source` section). If your repository requires either
a custom certificate authority or client certificates, similarly refer to the example above to configure the
`certificates` section. Poetry will use these values to authenticate to your private repository when downloading or
looking for packages.


### Disabling the PyPI repository

If you want your packages to be exclusively looked up from a private
repository, you can set it as the default:

**pyproject.toml**
```toml
[[tool.poetry.source]]
name = "foo"
url = "https://foo.bar/simple/"
default = true
```

**CLI**
```bash
poetry config repositories.foo.default true
```

**config.toml**
```toml
[repositories.foo]
name = "foo"
url = "https://foo.bar/simple/"
default = true
```


```toml
[[tool.poetry.source]]
name = "foo"
url = "https://foo.bar/simple/"
default = true
```

!!!note
    Only one default source can be marked as default.
    If there is a repository marked as default in the global config marked as default - project specific one will be ignored.
    This is behavior similar to PIP's `index-url` settings in `pip.conf`, see #1632 for more details.
