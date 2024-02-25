---
title: "The pyproject.toml file"
draft: false
type: docs
layout: single

menu:
  docs:
    weight: 90
---

# The `pyproject.toml` file

The `tool.poetry` section of the `pyproject.toml` file is composed of multiple sections.

## package-mode

Whether Poetry operates in package mode (default) or not. **Optional**

See [basic usage]({{< relref "basic-usage#operating-modes" >}}) for more information.

```toml
package-mode = false
```

## name

The name of the package. **Required in package mode**

This should be a valid name as defined by [PEP 508](https://peps.python.org/pep-0508/#names).


```toml
name = "my-package"
```

## version

The version of the package. **Required in package mode**

This should be a valid [PEP 440](https://peps.python.org/pep-0440/) string.

```toml
version = "0.1.0"
```

{{% note %}}

If you would like to use semantic versioning for your project, please see
[here]({{< relref "libraries#versioning" >}}).

{{% /note %}}

## description

A short description of the package. **Required in package mode**

```toml
description = "A short description of the package."
```

## license

The license of the package.

The recommended notation for the most common licenses is (alphabetical):

* Apache-2.0
* BSD-2-Clause
* BSD-3-Clause
* BSD-4-Clause
* GPL-2.0-only
* GPL-2.0-or-later
* GPL-3.0-only
* GPL-3.0-or-later
* LGPL-2.1-only
* LGPL-2.1-or-later
* LGPL-3.0-only
* LGPL-3.0-or-later
* MIT

Optional, but it is highly recommended to supply this.
More identifiers are listed at the [SPDX Open Source License Registry](https://spdx.org/licenses/).

```toml
license = "MIT"
```
{{% note %}}
If your project is proprietary and does not use a specific licence, you can set this value as `Proprietary`.
{{% /note %}}

## authors

The authors of the package. **Required in package mode**

This is a list of authors and should contain at least one author. Authors must be in the form `name <email>`.

```toml
authors = [
    "Sébastien Eustace <sebastien@eustace.io>",
]
```

## maintainers

The maintainers of the package. **Optional**

This is a list of maintainers and should be distinct from authors. Maintainers may contain an email and be in the form `name <email>`.

```toml
maintainers = [
    "John Smith <johnsmith@example.org>",
    "Jane Smith <janesmith@example.org>",
]
```

## readme

A path, or list of paths corresponding to the README file(s) of the package.
**Optional**

The file(s) can be of any format, but if you intend to publish to PyPI keep the
[recommendations for a PyPI-friendly README](
https://packaging.python.org/en/latest/guides/making-a-pypi-friendly-readme/) in
mind. README paths are implicitly relative to `pyproject.toml`.

{{% note %}}
Whether paths are case-sensitive follows platform defaults, but it is recommended to keep cases.

To be specific, you can set `readme = "rEaDmE.mD"` for `README.md` on macOS and Windows, but Linux users can't `poetry install` after cloning your repo. This is because macOS and Windows are case-insensitive and case-preserving.
{{% /note %}}

The contents of the README file(s) are used to populate the [Description
field](https://packaging.python.org/en/latest/specifications/core-metadata/#description-optional)
of your distribution's metadata (similar to `long_description` in setuptools).
When multiple files are specified they are concatenated with newlines.

```toml
[tool.poetry]
# ...
readme = "README.md"
```

```toml
[tool.poetry]
# ...
readme = ["docs/README1.md", "docs/README2.md"]
```

## homepage

An URL to the website of the project. **Optional**

```toml
homepage = "https://python-poetry.org/"
```

## repository

An URL to the repository of the project. **Optional**

```toml
repository = "https://github.com/python-poetry/poetry"
```

## documentation

An URL to the documentation of the project. **Optional**

```toml
documentation = "https://python-poetry.org/docs/"
```

## keywords

A list of keywords that the package is related to. **Optional**

```toml
keywords = ["packaging", "poetry"]
```

## classifiers

A list of PyPI [trove classifiers](https://pypi.org/classifiers/) that describe the project. **Optional**

```toml
[tool.poetry]
# ...
classifiers = [
    "Topic :: Software Development :: Build Tools",
    "Topic :: Software Development :: Libraries :: Python Modules"
]
```

{{% note %}}
Note that Python classifiers are still automatically added for you and are determined by your `python` requirement.

The `license` property will also set the License classifier automatically.
{{% /note %}}

## packages

A list of packages and modules to include in the final distribution.

If your project structure differs from the standard one supported by `poetry`,
you can specify the packages you want to include in the final distribution.

```toml
[tool.poetry]
# ...
packages = [
    { include = "my_package" },
    { include = "extra_package/**/*.py" },
]
```

If your package is stored inside a "lib" directory, you must specify it:

```toml
[tool.poetry]
# ...
packages = [
    { include = "my_package", from = "lib" },
]
```

The `to` parameter is designed to specify the relative destination path
where the package will be located upon installation. This allows for
greater control over the organization of packages within your project's structure.

```toml
[tool.poetry]
# ...
packages = [
    { include = "my_package", from = "lib", to = "target_package" },
]
```

If you want to restrict a package to a specific build format you can specify
it by using `format`:

```toml
[tool.poetry]
# ...
packages = [
    { include = "my_package" },
    { include = "my_other_package", format = "sdist" },
]
```

From now on, only the `sdist` build archive will include the `my_other_package` package.

{{% note %}}
Using `packages` disables the package auto-detection feature meaning you have to
**explicitly** specify the "default" package.

For instance, if you have a package named `my_package` and you want to also include
another package named `extra_package`, you will need to specify `my_package` explicitly:

```toml
packages = [
    { include = "my_package" },
    { include = "extra_package" },
]
```
{{% /note %}}

{{% note %}}
Poetry is clever enough to detect Python subpackages.

Thus, you only have to specify the directory where your root package resides.
{{% /note %}}

## include and exclude

A list of patterns that will be included in the final package.

You can explicitly specify to Poetry that a set of globs should be ignored or included for the purposes of packaging.
The globs specified in the exclude field identify a set of files that are not included when a package is built.

If a VCS is being used for a package, the exclude field will be seeded with the VCS’ ignore settings (`.gitignore` for git for example).

{{% note %}}
Explicitly declaring entries in `include` will negate VCS' ignore settings.
{{% /note %}}

```toml
[tool.poetry]
# ...
include = ["CHANGELOG.md"]
```

You can also specify the formats for which these patterns have to be included, as shown here:

```toml
[tool.poetry]
# ...
include = [
    { path = "tests", format = "sdist" },
    { path = "for_wheel.txt", format = ["sdist", "wheel"] }
]
```

If no format is specified, `include` defaults to only `sdist`.

In contrast, `exclude` defaults to both `sdist` and `wheel`.

```toml
exclude = ["my_package/excluded.py"]
```

## dependencies and dependency groups

Poetry is configured to look for dependencies on [PyPI](https://pypi.org) by default.
Only the name and a version string are required in this case.

```toml
[tool.poetry.dependencies]
requests = "^2.13.0"
```

If you want to use a [private repository]({{< relref "repositories#using-a-private-repository" >}}),
you can add it to your `pyproject.toml` file, like so:

```toml
[[tool.poetry.source]]
name = "private"
url = "http://example.com/simple"
```

If you have multiple repositories configured, you can explicitly tell poetry where to look for a specific package:

```toml
[tool.poetry.dependencies]
requests = { version = "^2.13.0", source = "private" }
```

{{% note %}}
Be aware that declaring the python version for which your package
is compatible is mandatory:

```toml
[tool.poetry.dependencies]
python = "^3.7"
```
{{% /note %}}

You can organize your dependencies in [groups]({{< relref "managing-dependencies#dependency-groups" >}})
to manage them in a more granular way.

```toml
[tool.poetry.group.test.dependencies]
pytest = "*"

[tool.poetry.group.docs.dependencies]
mkdocs = "*"
```

See [Dependency groups]({{< relref "managing-dependencies#dependency-groups" >}}) for a more in-depth look
at how to manage dependency groups and [Dependency specification]({{< relref "dependency-specification" >}})
for more information on other keys and specifying version ranges.

## `scripts`

This section describes the scripts or executables that will be installed when installing the package

```toml
[tool.poetry.scripts]
my_package_cli = 'my_package.console:run'
```

Here, we will have the `my_package_cli` script installed which will execute the `run` function in the `console` module in the `my_package` package.

{{% note %}}
When a script is added or updated, run `poetry install` to make them available in the project's virtualenv.
{{% /note %}}

## `extras`

Poetry supports extras to allow expression of:

* optional dependencies, which enhance a package, but are not required; and
* clusters of optional dependencies.

```toml
[tool.poetry]
name = "awesome"

[tool.poetry.dependencies]
# These packages are mandatory and form the core of this package’s distribution.
mandatory = "^1.0"

# A list of all of the optional dependencies, some of which are included in the
# below `extras`. They can be opted into by apps.
psycopg2 = { version = "^2.9", optional = true }
mysqlclient = { version = "^1.3", optional = true }

[tool.poetry.extras]
mysql = ["mysqlclient"]
pgsql = ["psycopg2"]
databases = ["mysqlclient", "psycopg2"]
```

When installing packages with Poetry, you can specify extras by using the `-E|--extras` option:

```bash
poetry install --extras "mysql pgsql"
poetry install -E mysql -E pgsql
```

Any extras you don't specify will be removed. Note this behavior is different from
[optional dependency groups]({{< relref "managing-dependencies#optional-groups" >}}) not
selected for install, e.g. those not specified via `install --with`.

You can install all extras with the `--all-extras` option:

```bash
poetry install --all-extras
```

{{% note %}}
Note that `install --extras` and the variations mentioned above (`--all-extras`, `--extras foo`, etc.) only work on dependencies defined in the current project. If you want to install extras defined by dependencies, you'll have to express that in the dependency itself:
```toml
[tool.poetry.group.dev.dependencies]
fastapi = {version="^0.92.0", extras=["all"]}
```
{{% /note %}}

When installing or specifying Poetry-built packages, the extras defined in this section can be activated
as described in [PEP 508](https://www.python.org/dev/peps/pep-0508/#extras).

For example, when installing the package using `pip`, the dependencies required by
the `databases` extra can be installed as shown below.

```bash
pip install awesome[databases]
```

{{% note %}}
The dependencies specified for each `extra` must already be defined as project dependencies.

Dependencies listed in [dependency groups]({{< relref "managing-dependencies#dependency-groups" >}}) cannot be specified as extras.
{{% /note %}}


## `plugins`

Poetry supports arbitrary plugins, which are exposed as the ecosystem-standard [entry points](https://packaging.python.org/en/latest/specifications/entry-points/) and discoverable using `importlib.metadata`. This is similar to (and compatible with) the entry points feature of `setuptools`.
The syntax for registering a plugin is:

```toml
[tool.poetry.plugins] # Optional super table

[tool.poetry.plugins."A"]
B = "C:D"
```
Which are:

- `A` - type of the plugin, for example `poetry.plugin` or `flake8.extension`
- `B` - name of the plugin
- `C` - python module import path
- `D` - the entry point of the plugin (a function or class)

Example (from [`poetry-plugin-export`](http://github.com/python-poetry/poetry-plugin-export)):

```toml
[tool.poetry.plugins."poetry.application.plugin"]
export = "poetry_plugin_export.plugins:ExportApplicationPlugin"
```

## `urls`

In addition to the basic urls (`homepage`, `repository` and `documentation`), you can specify
any custom url in the `urls` section.

```toml
[tool.poetry.urls]
"Bug Tracker" = "https://github.com/python-poetry/poetry/issues"
```

If you publish your package on PyPI, they will appear in the `Project Links` section.

## Poetry and PEP-517

[PEP-517](https://www.python.org/dev/peps/pep-0517/) introduces a standard way
to define alternative build systems to build a Python project.

Poetry is compliant with PEP-517, by providing a lightweight core library,
so if you use Poetry to manage your Python project you should reference
it in the `build-system` section of the `pyproject.toml` file like so:

```toml
[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```

{{% note %}}
When using the `new` or `init` command this section will be automatically added.
{{% /note %}}

{{% note %}}
If your `pyproject.toml` file still references `poetry` directly as a build backend,
you should update it to reference `poetry-core` instead.
{{% /note %}}
