---
title: "Repositories"
draft: false
type: docs
layout: "docs"

menu:
  docs:
    weight: 50
---

# Repositories

Poetry supports the use of [PyPI](https://pypi.org) and private repositories for discovery of
packages as well as for publishing your projects.

By default, Poetry is configured to use the [PyPI](https://pypi.org) repository,
for package installation and publishing.

So, when you add dependencies to your project, Poetry will assume they are available
on PyPI.

This represents most cases and will likely be enough for most users.

### Private Repository Example

#### Installing from private package sources
By default, Poetry discovers and installs packages from [PyPI](https://pypi.org). But, you want to
install a dependency to your project for a [simple API repository](#simple-api-repository)? Let's
do it.

First, [configure](#project-configuration) the [package source](#package-source) as a [secondary package source](#secondary-package-sources) to your
project.

```bash
poetry source add --secondary foo https://pypi.example.org/simple/
```

Then, assuming the repository requires authentication, configure credentials for it.

```bash
poetry config http-basic.foo username password
```

Once this is done, you can add dependencies to your project from this source.

```bash
poetry add --source foo private-package
```

#### Publishing to a private repository

Great, now all that is left is to publish your package. Assuming you'd want to share it privately
with your team, you can configure the
[Upload API](https://warehouse.pypa.io/api-reference/legacy.html#upload-api) endpoint for your
[publishable repository](#publishable-repository).

```bash
poetry config repositories.foo https://pypi.example.org/legacy/
```

{{% note %}}

If you need to use a different credential for your [package source](#package-sources), then it is
recommended to use a different name for your publishing repository.

```bash
poetry config repositories.foo-pub https://pypi.example.org/legacy/
poetry config http-basic.foo-pub username password
```

{{% /note %}}

Now, all the is left is to build and publish your project using the
[`publish`]({{< relref "cli#publish" >}}).

```bash
poetry publish --build --repository foo-pub
```

## Package Sources

By default, Poetry is configured to use the Python ecosystem's canonical package index
[PyPI](https://pypi.org).

{{% note %}}

With the exception of the implicitly configured source for [PyPI](https://pypi.org) named `pypi`,
package sources are local to a project and must be configured within the project's
[`pyproject.toml`]({{< relref "pyproject" >}}) file. This is **not** the same configuration used
when publishing a package.

{{% /note %}}

### Project Configuration

These package sources may be managed using the [`source`]({{< relref "cli#source" >}}) command for
your project.

```bash
poetry source add foo https://foo.bar/simple/
```

{{% note %}}

If your package source requires [credentials](#configuring-credentials) or
[certificates](#certificates), please refer to the relevant sections below.

{{% /note %}}

This will generate the following configuration snippet in your
[`pyproject.toml`]({{< relref "pyproject" >}}) file.

```toml
[[tool.poetry.source]]
name = "foo"
url = "https://foo.bar/simple/"
default = false
secondary = false
```

Any package source defined like this takes precedence over [PyPI](https://pypi.org).


{{% note %}}

If you prefer to disable [PyPI](https://pypi.org) completely, you may choose to set one of your package sources to be the [default](#default-package-source).

If you prefer to specify a package source for a specific dependency, see [Secondary Package Sources](#secondary-package-sources).

{{% /note %}}


{{% warning %}}

If you do not want any of the custom sources to take precedence over [PyPI](https://pypi.org),
you must declare **all** package sources to be [secondary](#secondary-package-sources).

{{% /warning %}}


#### Default Package Source

By default, Poetry configures [PyPI](https://pypi.org) as the default package source for your
project. You can alter this behaviour and exclusively look up packages only from the configured
package sources by adding a **single** source with `default = true`.

```bash
poetry source add --default foo https://foo.bar/simple/
```

{{% warning %}}

Configuring a custom package source as default, will effectively disable [PyPI](https://pypi.org)
as a package source for your project.

{{% /warning %}}

#### Secondary Package Sources

If package sources are configured as secondary, all it means is that these will be given a lower
priority when selecting compatible package distribution that also exists in your default package
source.

You can configure a package source as a secondary source with `secondary = true` in your package
source configuration.

```bash
poetry source add --secondary foo https://foo.bar/simple/
```

There can be more than one secondary package source.

{{% note %}}

All package sources (including secondary sources) will be searched during the package lookup
process. These network requests will occur for all sources, regardless of if the package is
found at one or more sources.

In order to limit the search for a specific package to a particular package source, you can explicitly specify what source to use.

```bash
poetry add --source internal-pypi httpx
```

```toml
[tool.poetry.dependencies]
...
httpx = { version = "^0.22", source = "internal-pypi" }

[[tool.poetry.source]]
name = "internal-pypi"
url = "https://foo.bar/simple/"
secondary = true
```

{{% /note %}}

### Supported Package Sources

#### Python Package Index (PyPI)

Poetry interacts with [PyPI](https://pypi.org) via its
[JSON API](https://warehouse.pypa.io/api-reference/json.html). This is used to retrieve a requested
package's versions, metadata, files, etc.

{{% note %}}

If the the package's published metadata is invalid, Poetry will download the available bdist/sdist to
inspect it locally to identify the relevant metadata.

{{% /note %}}

If you want to explicitly select a package from [PyPI](https://pypi.org) you can use the `--source`
option with the [`add`]({{< relref "cli#add" >}}) command, like shown below.

```bash
poetry add --source pypi httpx@^0.22.0
```

This will generate the following configuration snippet in your `pyproject.toml` file.

```toml
httpx = {version = "^0.22.0", source = "pypi"}
```

{{% warning %}}

If any source within a project is configured with `default = true`, The implicit `pypi` source will
be disabled and not used for any packages.

{{% /warning %}}

#### Simple API Repository

Poetry can fetch and install package dependencies from public or private custom repositories that
implement the simple repository API as described in [PEP 503](https://peps.python.org/pep-0503/).

{{% warning %}}

When using sources that distributes large wheels without providing file checksum in file URLs,
Poetry will download each candidate wheel at least once in order to generate the checksum. This can
manifest as long dependency resolution times when adding packages from this source.

{{% /warning %}}

These package sources maybe configured via the following command in your project.

```bash
poetry source add testpypi https://test.pypi.org/simple/
```

{{% note %}}

Note the trailing `/simple/`. This is important when configuring
[PEP 503](https://peps.python.org/pep-0503/) compliant package sources.

{{% /note %}}

In addition to [PEP 503](https://peps.python.org/pep-0503/), Poetry can also handle simple API
repositories that implement [PEP 658](https://peps.python.org/pep-0658/) (*Introduced in 1.2.0*).
This is helpful in reducing dependency resolution time for packages from these sources as Poetry can
avoid having to download each candidate distribution, in order to determine associated metadata.

{{% note %}}

*Why does Poetry insist on downloading all candidate distributions for all platforms when metadata
is not available?*

The need for this stems from the fact that Poetry's lock file is platform-agnostic. This means, in
order to resolve dependencies for a project, Poetry needs metadata for all platform specific
distributions. And when this metadata is not readily available, downloading the distribution and
inspecting it locally is the only remaining option.

{{% /note %}}

#### Single Page Link Source

*Introduced in 1.2.0*

Some projects choose to release their binary distributions via a single page link source that
partially follows the structure of a package page in [PEP 503](https://peps.python.org/pep-0503/).

These package sources maybe configured via the following command in your project.

```bash
poetry source add jax https://storage.googleapis.com/jax-releases/jax_releases.html
```

{{% note %}}

All caveats regarding slower resolution times described for simple API repositories do apply here as
well.

{{% /note %}}


## Publishable Repositories

Poetry treats repositories to which you publish packages as user specific and not project specific
configuration unlike [package sources](#package-sources). Poetry, today, only supports the
[Legacy Upload API](https://warehouse.pypa.io/api-reference/legacy.html#upload-api) when publishing
your project.

These are configured using the [`config`]({{< relref "cli#config" >}}) command, under the
`repository` key.

```bash
poetry config repository.testpypi https://upload.test.pypi.org/legacy/
```

{{% note %}}

[Legacy Upload API](https://warehouse.pypa.io/api-reference/legacy.html#upload-api) URLs are
typically different to the same one provided by the repository for the simple API. You'll note that
in the example of [Test PyPI](https://test.pypi.org/), both the host (`upload.test.pypi.org`) as
well as the path (`/legacy`) are different to it's simple API (`https://test.pypi.org/simple`).

{{% /note %}}

## Configuring Credentials

If you want to store your credentials for a specific repository, you can do so easily:

```bash
poetry config http-basic.foo username password
```

If you do not specify the password you will be prompted to write it.

{{% note %}}

To publish to PyPI, you can set your credentials for the repository named `pypi`.

Note that it is recommended to use [API tokens](https://pypi.org/help/#apitoken)
when uploading packages to PyPI.
Once you have created a new token, you can tell Poetry to use it:

```bash
poetry config pypi-token.pypi my-token
```

If you still want to use your username and password, you can do so with the following
call to `config`.

```bash
poetry config http-basic.pypi username password
```

{{% /note %}}

You can also specify the username and password when using the `publish` command
with the `--username` and `--password` options.

If a system keyring is available and supported, the password is stored to and retrieved from the keyring. In the above example, the credential will be stored using the name `poetry-repository-pypi`. If access to keyring fails or is unsupported, this will fall back to writing the password to the `auth.toml` file along with the username.

Keyring support is enabled using the [keyring library](https://pypi.org/project/keyring/). For more information on supported backends refer to the [library documentation](https://keyring.readthedocs.io/en/latest/?badge=latest).

{{% note %}}

Poetry will fallback to Pip style use of keyring so that backends like
Microsoft's [artifacts-keyring](https://pypi.org/project/artifacts-keyring/) get a change to retrieve
valid credentials. It will need to be properly installed into Poetry's virtualenv,
preferably by installing a plugin.

If you are letting Poetry manage your virtual environments you will want a virtualenv
seeder installed in Poetry's virtualenv that installs the desired keyring backend
during `poetry install`. To again use Azure DevOps as an example: [azure-devops-artifacts-helpers](https://pypi.org/project/azure-devops-artifacts-helpers/)
provides such a seeder. This would of course best achieved by installing a Poetry plugin
if it exists for you use case instead of doing it yourself.

{{% /note %}}

Alternatively, you can use environment variables to provide the credentials:

```bash
export POETRY_PYPI_TOKEN_PYPI=my-token
export POETRY_HTTP_BASIC_PYPI_USERNAME=username
export POETRY_HTTP_BASIC_PYPI_PASSWORD=password
```

See [Using environment variables]({{< relref "configuration#using-environment-variables" >}}) for more information
on how to configure Poetry with environment variables.

If your password starts with a dash (e.g. randomly generated tokens in a CI environment), it will be parsed as a
command line option instead of a password.
You can prevent this by adding double dashes to prevent any following argument from being parsed as an option.

```bash
poetry config -- http-basic.pypi myUsername -myPasswordStartingWithDash
```

## Certificates

### Custom certificate authority and mutual TLS authentication

Poetry supports repositories that are secured by a custom certificate authority as well as those that require
certificate-based client authentication.  The following will configure the "foo" repository to validate the repository's
certificate using a custom certificate authority and use a client certificate (note that these config variables do not
both need to be set):

```bash
poetry config certificates.foo.cert /path/to/ca.pem
poetry config certificates.foo.client-cert /path/to/client.pem
```

## Caches

Poetry employs multiple caches for package sources in order to improve user experience and avoid duplicate network
requests.

The first level cache is a [Cache-Control](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control)
header based cache for almost all HTTP requests.

Further, every HTTP backed package source caches metadata associated with a package once it is fetched or generated.
Additionally, downloaded files (package distributions) are also cached.

## Debugging Issues
If you encounter issues with package sources, one of the simplest steps you might take to debug an issue is rerunning
your command with the `--no-cache` flag.

```bash
poetry --no-cache add pycowsay
```

If this solves your issue, you can consider clearing your cache using the [`cache`]({{< relref "cli#cache-clear" >}})
command.

Alternatively, you could also consider enabling very verbose loging `-vvv` along with the `--no-cache` to see network
requests being made in the logs.
