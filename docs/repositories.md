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

First, [configure](#project-configuration) the [package source](#package-sources) as a [supplemental](#supplemental-package-sources) (or [explicit](#explicit-package-sources)) package source to your
project.

```bash
poetry source add --priority=supplemental foo https://pypi.example.org/simple/
```

Then, assuming the repository requires authentication, configure credentials for it.

```bash
poetry config http-basic.foo <username> <password>
```

{{% warning %}}
Depending on your system configuration, credentials might be saved in your command line history.
Many shells do not save commands to history when they are prefixed by a space character. For more information, please refer to your shell's documentation.
{{% /warning %}}

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
poetry config http-basic.foo-pub <username> <password>
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
priority = "primary"
```

If `priority` is undefined, the source is considered a primary source that takes precedence over PyPI, secondary, supplemental and explicit sources.

Package sources are considered in the following order:
1. [default source](#default-package-source-deprecated) (DEPRECATED),
2. [primary sources](#primary-package-sources),
3. implicit PyPI (unless disabled by another [primary source](#primary-package-sources), [default source](#default-package-source-deprecated) or configured explicitly),
4. [secondary sources](#secondary-package-sources-deprecated) (DEPRECATED),
5. [supplemental sources](#supplemental-package-sources).

[Explicit sources](#explicit-package-sources) are considered only for packages that explicitly [indicate their source](#package-source-constraint).

Within each priority class, package sources are considered in order of appearance in `pyproject.toml`.

{{% note %}}

If you want to change the priority of [PyPI](https://pypi.org), you can set it explicitly, e.g.

```bash
poetry source add --priority=primary PyPI
```

If you prefer to disable PyPI completely,
just add a [primary source](#primary-package-sources)
or configure PyPI as [explicit source](#explicit-package-sources).

{{% /note %}}


#### Default Package Source (DEPRECATED)

*Deprecated in 1.8.0*

{{% warning %}}

Configuring a default package source is deprecated because it is the same
as the topmost [primary source](#primary-package-sources).
Just configure a primary package source and put it first in the list of package sources.

{{% /warning %}}

By default, if you have not configured any primary source,
Poetry will configure [PyPI](https://pypi.org) as the package source for your project.
You can alter this behaviour and exclusively look up packages only from the configured
package sources by adding at least one primary source (recommended)
or a **single** source with `priority = "default"` (deprecated).

```bash
poetry source add --priority=default foo https://foo.bar/simple/
```


#### Primary Package Sources

All primary package sources are searched for each dependency without a [source constraint](#package-source-constraint).
If you configure at least one primary source, the implicit PyPI source is disabled.

```bash
poetry source add --priority=primary foo https://foo.bar/simple/
```

Sources without a priority are considered primary sources, too.

```bash
poetry source add foo https://foo.bar/simple/
```

{{% warning %}}

The implicit PyPI source is disabled automatically if at least one primary source is configured.
If you want to use PyPI in addition to a primary source, configure it explicitly
with a certain priority, e.g.

```bash
poetry source add --priority=primary PyPI
```

This way, the priority of PyPI can be set in a fine-granular way.

The equivalent specification in `pyproject.toml` is:

```toml
[[tool.poetry.source]]
name = "pypi"
priority = "primary"
```

**Omit the `url` when specifying PyPI explicitly.** Because PyPI is internally configured
with Poetry, the PyPI repository cannot be configured with a given URL. Remember, you can always use
`poetry check` to ensure the validity of the `pyproject.toml` file.

{{% /warning %}}

#### Secondary Package Sources (DEPRECATED)

*Deprecated in 1.5.0*

If package sources are configured as secondary, all it means is that these will be given a lower
priority when selecting compatible package distribution that also exists in your default and primary package sources. If the package source should instead be searched only if higher-priority repositories did not return results, please consider a [supplemental source](#supplemental-package-sources) instead.

You can configure a package source as a secondary source with `priority = "secondary"` in your package
source configuration.

```bash
poetry source add --priority=secondary foo https://foo.bar/simple/
```

There can be more than one secondary package source.

{{% warning %}}

Secondary package sources are deprecated in favor of supplemental package sources.

{{% /warning %}}

#### Supplemental Package Sources

*Introduced in 1.5.0*

Package sources configured as supplemental are only searched if no other (higher-priority) source yields a compatible package distribution. This is particularly convenient if the response time of the source is high and relatively few package distributions are to be fetched from this source.

You can configure a package source as a supplemental source with `priority = "supplemental"` in your package
source configuration.

```bash
poetry source add --priority=supplemental foo https://foo.bar/simple/
```

There can be more than one supplemental package source.

{{% warning %}}

Take into account that someone could publish a new package to a primary source
which matches a package in your supplemental source. They could coincidentally
or intentionally replace your dependency with something you did not expect.

{{% /warning %}}


#### Explicit Package Sources

*Introduced in 1.5.0*

If package sources are configured as explicit, these sources are only searched when a package configuration [explicitly indicates](#package-source-constraint) that it should be found on this package source.

You can configure a package source as an explicit source with `priority = "explicit"` in your package source configuration.

```bash
poetry source add --priority=explicit foo https://foo.bar/simple/
```

There can be more than one explicit package source.

{{% note %}}
A real-world example where an explicit package source is useful, is for PyTorch GPU packages.

```bash
poetry source add --priority=explicit pytorch-gpu-src https://download.pytorch.org/whl/cu118
poetry add --source pytorch-gpu-src torch torchvision torchaudio
```
{{% /note %}}

#### Package Source Constraint

All package sources (including secondary and possibly supplemental sources) will be searched during the package lookup
process. These network requests will occur for all sources, regardless of if the package is
found at one or more sources.

In order to limit the search for a specific package to a particular package repository, you can specify the source explicitly.

```bash
poetry add --source internal-pypi httpx
```

This results in the following configuration in `pyproject.toml`:

```toml
[tool.poetry.dependencies]
...
httpx = { version = "^0.22", source = "internal-pypi" }

[[tool.poetry.source]]
name = "internal-pypi"
url = ...
priority = ...
```

{{% note %}}

A repository that is configured to be the only source for retrieving a certain package can itself have any priority.
In particular, it does not need to have priority `"explicit"`.
If a repository is configured to be the source of a package, it will be the only source that is considered for that package
and the repository priority will have no effect on the resolution.

{{% /note %}}

{{% note %}}

Package `source` keys are not inherited by their dependencies.
In particular, if `package-A` is configured to be found in `source = internal-pypi`,
and `package-A` depends on `package-B` that is also to be found on `internal-pypi`,
then `package-B` needs to be configured as such in `pyproject.toml`.
The easiest way to achieve this is to add `package-B` with a wildcard constraint:

```bash
poetry add --source internal-pypi package-B@*
```

This will ensure that `package-B` is searched only in the `internal-pypi` package source.
The version constraints on `package-B` are derived from `package-A` (and other client packages), as usual.

If you want to avoid additional main dependencies,
you can add `package-B` to a dedicated [dependency group]({{< relref "managing-dependencies#dependency-groups" >}}):

```bash
poetry add --group explicit --source internal-pypi package-B@*
```

{{% /note %}}

{{% note %}}

Package source constraints are strongly suggested for all packages that are expected
to be provided only by one specific source to avoid dependency confusion attacks.

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

If any source within a project is configured with `priority = "default"`, The implicit `pypi` source will
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

These package sources may be configured via the following command in your project.

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

These package sources may be configured via the following command in your project.

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
`repositories` key.

```bash
poetry config repositories.testpypi https://test.pypi.org/legacy/
```

{{% note %}}

[Legacy Upload API](https://warehouse.pypa.io/api-reference/legacy.html#upload-api) URLs are
typically different to the same one provided by the repository for the simple API. You'll note that
in the example of [Test PyPI](https://test.pypi.org/), both the host (`test.pypi.org`) as
well as the path (`/legacy`) are different to its simple API (`https://test.pypi.org/simple`).

{{% /note %}}

## Configuring Credentials

If you want to store your credentials for a specific repository, you can do so easily:

```bash
poetry config http-basic.foo <username> <password>
```

If you do not specify the password you will be prompted to write it.

{{% note %}}

To publish to PyPI, you can set your credentials for the repository named `pypi`.

Note that it is recommended to use [API tokens](https://pypi.org/help/#apitoken)
when uploading packages to PyPI.
Once you have created a new token, you can tell Poetry to use it:

```bash
poetry config pypi-token.pypi <my-token>
```

If you still want to use your username and password, you can do so with the following
call to `config`.

```bash
poetry config http-basic.pypi <username> <password>
```

{{% /note %}}

You can also specify the username and password when using the `publish` command
with the `--username` and `--password` options.

If a system keyring is available and supported, the password is stored to and retrieved from the keyring. In the above example, the credential will be stored using the name `poetry-repository-pypi`. If access to keyring fails or is unsupported, this will fall back to writing the password to the `auth.toml` file along with the username.

Keyring support is enabled using the [keyring library](https://pypi.org/project/keyring/). For more information on supported backends refer to the [library documentation](https://keyring.readthedocs.io/en/latest/?badge=latest).

If you do not want to use the keyring, you can tell Poetry to disable it and store the credentials in plaintext config files:

```bash
poetry config keyring.enabled false
```

{{% note %}}

Poetry will fallback to Pip style use of keyring so that backends like
Microsoft's [artifacts-keyring](https://pypi.org/project/artifacts-keyring/) get a chance to retrieve
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
export POETRY_PYPI_TOKEN_FOO=my-token
export POETRY_HTTP_BASIC_FOO_USERNAME=<username>
export POETRY_HTTP_BASIC_FOO_PASSWORD=<password>
```

where `FOO` is the name of the repository in uppercase (e.g. `PYPI`).
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

{{% note %}}
The value of `certificates.<repository>.cert` can be set to `false` if certificate verification is
required to be skipped. This is useful for cases where a package source with self-signed certificates
are used.

```bash
poetry config certificates.foo.cert false
```

{{% warning %}}
Disabling certificate verification is not recommended as it is does not conform to security
best practices.
{{% /warning %}}
{{% /note %}}

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

Alternatively, you could also consider enabling very verbose logging `-vvv` along with the `--no-cache` to see network
requests being made in the logs.
